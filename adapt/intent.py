# Copyright 2018 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__author__ = 'seanfitz'

import itertools

CLIENT_ENTITY_NAME = 'Client'


def is_entity(tag, entity_name):
    for entity in tag.get('entities'):
        for v, t in entity.get('data'):
            if t.lower() == entity_name.lower():
                return True
    return False


def find_first_tag(tags, entity_type, after_index=-1):
    """Searches tags for entity type after given index

    Args:
        tags(list): a list of tags with entity types to be compared to
         entity_type
        entity_type(str): This is he entity type to be looking for in tags
        after_index(int): the start token must be greater than this.

    Returns:
        ( tag, v, confidence ):
            tag(str): is the tag that matched
            v(str): ? the word that matched?
            confidence(float): is a measure of accuracy.  1 is full confidence
                and 0 is none.
    """
    for tag in tags:
        for entity in tag.get('entities'):
            for v, t in entity.get('data'):
                if t.lower() == entity_type.lower() and \
                        (tag.get('start_token', 0) > after_index or \
                         tag.get('from_context', False)):
                    return tag, v, entity.get('confidence')

    return None, None, None


def find_next_tag(tags, end_index=0):
    for tag in tags:
        if tag.get('start_token') > end_index:
            return tag
    return None


def choose_1_from_each(lists):
    """
    The original implementation here was functionally equivalent to
    :func:`~itertools.product`, except that the former returns a generator
    of lists, and itertools returns a generator of tuples. This is going to do
    a light transform for now, until callers can be verified to work with
    tuples.

    Args:
        A list of lists or tuples, expected as input to
        :func:`~itertools.product`

    Returns:
        a generator of lists, see docs on :func:`~itertools.product`
    """
    for result in itertools.product(*lists):
        yield list(result)


def resolve_one_of(tags, at_least_one):
    """Search through all combinations of at_least_one rules to find a
    combination that is covered by tags

    Args:
        tags(list): List of tags with Entities to search for Entities
        at_least_one(list): List of Entities to find in tags

    Returns:
        object:
        returns None if no match is found but returns any match as an object
    """

    for possible_resolution in choose_1_from_each(at_least_one):
        resolution = {}
        pr = possible_resolution[:]
        for entity_type in pr:
            last_end_index = -1
            if entity_type in resolution:
                last_end_index = resolution[entity_type][-1].get('end_token')
            tag, value, c = find_first_tag(tags, entity_type,
                                           after_index=last_end_index)
            if not tag:
                break
            else:
                if entity_type not in resolution:
                    resolution[entity_type] = []
                resolution[entity_type].append(tag)
        # Check if this is a valid resolution (all one_of rules matched)
        if len(resolution) == len(possible_resolution):
            return resolution

    return None


class Intent(object):
    def __init__(self, name, requires, at_least_one, optional):
        """Create Intent object

        Args:
            name(str): Name for Intent
            requires(list): Entities that are required
            at_least_one(list): One of these Entities are required
            optional(list): Optional Entities used by the intent
        """
        self.name = name
        self.requires = requires
        self.at_least_one = at_least_one
        self.optional = optional

    def validate(self, tags, confidence):
        """Using this method removes tags from the result of validate_with_tags

        Returns:
            intent(intent): Results from validate_with_tags
        """
        intent, tags = self.validate_with_tags(tags, confidence)
        return intent

    def validate_with_tags(self, tags, confidence):
        """Validate whether tags has required entites for this intent to fire

        Args:
            tags(list): Tags and Entities used for validation
            confidence(float): The weight associate to the parse result,
                as indicated by the parser. This is influenced by a parser
                that uses edit distance or context.

        Returns:
            intent, tags: Returns intent and tags used by the intent on
                failure to meat required entities then returns intent with
                confidence
                of 0.0 and an empty list for tags.
        """
        result = {'intent_type': self.name}
        intent_confidence = 0.0
        local_tags = tags[:]
        used_tags = []

        for require_type, attribute_name in self.requires:
            required_tag, canonical_form, tag_confidence = \
                find_first_tag(local_tags, require_type)
            if not required_tag:
                result['confidence'] = 0.0
                return result, []

            result[attribute_name] = canonical_form
            if required_tag in local_tags:
                local_tags.remove(required_tag)
            used_tags.append(required_tag)
            intent_confidence += tag_confidence

        if len(self.at_least_one) > 0:
            best_resolution = resolve_one_of(local_tags, self.at_least_one)
            if not best_resolution:
                result['confidence'] = 0.0
                return result, []
            else:
                for key in best_resolution:
                    # TODO: at least one should support aliases
                    result[key] = best_resolution[key][0].get('key')
                    intent_confidence += \
                        1.0 * best_resolution[key][0]['entities'][0]\
                        .get('confidence', 1.0)
                used_tags.append(best_resolution[key][0])
                if best_resolution in local_tags:
                    local_tags.remove(best_resolution[key][0])

        for optional_type, attribute_name in self.optional:
            optional_tag, canonical_form, tag_confidence = \
                find_first_tag(local_tags, optional_type)
            if not optional_tag or attribute_name in result:
                continue
            result[attribute_name] = canonical_form
            if optional_tag in local_tags:
                local_tags.remove(optional_tag)
            used_tags.append(optional_tag)
            intent_confidence += tag_confidence

        total_confidence = (intent_confidence / len(tags) * confidence) \
            if tags else 0.0

        target_client, canonical_form, confidence = \
            find_first_tag(local_tags, CLIENT_ENTITY_NAME)

        result['target'] = target_client.get('key') if target_client else None
        result['confidence'] = total_confidence

        return result, used_tags


class IntentBuilder(object):
    """
    IntentBuilder, used to construct intent parsers.

    Attributes:
        at_least_one(list): A list of Entities where one is required.
            These are separated into lists so you can have one of (A or B) and
            then require one of (D or F).
        requires(list): A list of Required Entities
        optional(list): A list of optional Entities
        name(str): Name of intent

    Notes:
        This is designed to allow construction of intents in one line.

    Example:
        IntentBuilder("Intent")\
            .requires("A")\
            .one_of("C","D")\
            .optional("G").build()
    """
    def __init__(self, intent_name):
        """
        Constructor

        Args:
            intent_name(str): the name of the intents that this parser
            parses/validates
        """
        self.at_least_one = []
        self.requires = []
        self.optional = []
        self.name = intent_name

    def one_of(self, *args):
        """
        The intent parser should require one of the provided entity types to
        validate this clause.

        Args:
            args(args): *args notation list of entity names

        Returns:
            self: to continue modifications.
        """
        self.at_least_one.append(args)
        return self

    def require(self, entity_type, attribute_name=None):
        """
        The intent parser should require an entity of the provided type.

        Args:
            entity_type(str): an entity type
            attribute_name(str): the name of the attribute on the parsed intent.
            Defaults to match entity_type.

        Returns:
            self: to continue modifications.
        """
        if not attribute_name:
            attribute_name = entity_type
        self.requires += [(entity_type, attribute_name)]
        return self

    def optionally(self, entity_type, attribute_name=None):
        """
        Parsed intents from this parser can optionally include an entity of the
         provided type.

        Args:
            entity_type(str): an entity type
            attribute_name(str): the name of the attribute on the parsed intent.
            Defaults to match entity_type.

        Returns:
            self: to continue modifications.
        """
        if not attribute_name:
            attribute_name = entity_type
        self.optional += [(entity_type, attribute_name)]
        return self

    def build(self):
        """
        Constructs an intent from the builder's specifications.

        :return: an Intent instance.
        """
        return Intent(self.name, self.requires,
                      self.at_least_one, self.optional)
