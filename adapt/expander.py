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

from six.moves import xrange

__author__ = 'seanfitz'


class SimpleGraph(object):
    """This class is to graph connected nodes
    Note:
        hash is a type that is hashable so independant values and tuples
        but not objects, classes or lists.
    """

    def __init__(self):
        """init an empty set"""
        self.adjacency_lists = {}

    def add_edge(self, a, b):
        """Used to add edges to the graph. 'a' and 'b' are vertexes and
        if 'a' or 'b' doesn't exisit then the vertex is created

        Args:
            a (hash): is one vertex of the edge
            b (hash): is another vertext of the edge


        """
        neighbors_of_a = self.adjacency_lists.get(a)
        if not neighbors_of_a:
            neighbors_of_a = set()
            self.adjacency_lists[a] = neighbors_of_a

        neighbors_of_a.add(b)

        neighbors_of_b = self.adjacency_lists.get(b)
        if not neighbors_of_b:
            neighbors_of_b = set()
            self.adjacency_lists[b] = neighbors_of_b

        neighbors_of_b.add(a)

    def get_neighbors_of(self, a):
        """This will return the neighbors of the vertex

        Args:
            a (hash): is the vertex to get the neighbors for

        Returns:
            [] : a list of neighbors_of 'a'
                Will return an empty set if 'a' doesn't exist or has no
                neightbors.

        """
        return self.adjacency_lists.get(a, set())

    def vertex_set(self):
        """This returns a list of vertexes included in graph

        Returns:
            [] : a list of vertexes include in graph
        """
        return list(self.adjacency_lists)


def bronk(r, p, x, graph):
    """This is used to fine cliques and remove them from graph

    Args:
        graph (graph): this is the graph of verticies to search for
            cliques
        p (list): this is a list of the verticies to search
        r (list): used by bronk for the search
        x (list): used by bronk for the search

    Yields:
        list : found clique of the given graph and verticies
    """
    if len(p) == 0 and len(x) == 0:
        yield r
        return
    for vertex in p[:]:
        r_new = r[::]
        r_new.append(vertex)
        p_new = [val for val in p if val in graph.get_neighbors_of(vertex)] # p intersects N(vertex)
        x_new = [val for val in x if val in graph.get_neighbors_of(vertex)] # x intersects N(vertex)
        for result in bronk(r_new, p_new, x_new, graph):
            yield result
        p.remove(vertex)
        x.append(vertex)


def get_cliques(vertices, graph):
    """get cliques

    Args:
        verticies (list) : list of the verticies to search for cliques
        graph (graph) : a graph used to find the cliques using verticies

    Yields:
        list: a clique from the graph
    """
    for clique in bronk([], vertices, [], graph):
        yield clique


def graph_key_from_tag(tag, entity_index):
    """Returns a key from a tag entity

    Args:
        tag (tag) : this is the tag selected to get the key from
        entity_index (int) : this is the index of the tagged entity

    Returns:
        str : String representing the key for the given tagged entity.
    """
    start_token = tag.get('start_token')
    entity = tag.get('entities', [])[entity_index]
    return str(start_token) + '-' + entity.get('key') + '-' + str(entity.get('confidence'))


class Lattice(object):
    """This manages a list of items or lists

    Attributes:
        nodes (list) : is a list of items or lists.
            This is used to track items and lists that are a part of the
            Lattice
    """

    def __init__(self):
        """Creates the Lattice with an empty list"""
        self.nodes = []

    def append(self, data):
        """Appends items or lists to the Lattice

        Args:
            data (item,list) : The Item or List to be added to the Lattice
        """
        if isinstance(data, list) and len(data) > 0:
            self.nodes.append(data)
        else:
            self.nodes.append([data])

    def traverse(self, index=0):
        """ This is used to produce a list of lists where each each item
        in that list is a diffrent combination of items from the lists
        within with every combination of such values.

        Args:
            index (int) : the index at witch to start the list.
                Note this is used only in the function as a processing

        Returns:
            list : is every combination.
        """
        if index < len(self.nodes):
            for entity in self.nodes[index]:
                for next_result in self.traverse(index=index+1):
                    if isinstance(entity, list):
                        yield entity + next_result
                    else:
                        yield [entity] + next_result
        else:
            yield []


class BronKerboschExpander(object):
    """
    BronKerboschExpander

    Given a list of tagged entities (from the existing entity tagger implementation or another), expand out
    valid parse results.

    A parse result is considered valid if it contains no overlapping spans.

    Since total confidence of a parse result is based on the sum of confidences of the entities, there is no sense
    in yielding any potential parse results that are a subset/sequence of a larger valid parse result. By comparing
    this concept to that of maximal cliques (https://en.wikipedia.org/wiki/Clique_problem), we can use well known
    solutions to the maximal clique problem like the Bron/Kerbosch algorithm (https://en.wikipedia.org/wiki/Bron%E2%80%93Kerbosch_algorithm).

    By considering tagged entities that do not overlap to be "neighbors", BronKerbosch will yield a set of maximal
    cliques that are also valid parse results.
    """
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def _build_graph(self, tags):
        """Builds a graph from the entities included in the tags.
        Note this is used internally.

        Args:
            tags (list): A list of the tags to include in graph

        Returns:
            graph : this is the resulting graph of the tagged entities.

        """
        graph = SimpleGraph()
        for tag_index in xrange(len(tags)):
            for entity_index in xrange(len(tags[tag_index].get('entities'))):
                a_entity_name = graph_key_from_tag(tags[tag_index], entity_index)
                tokens = self.tokenizer.tokenize(tags[tag_index].get('entities', [])[entity_index].get('match'))
                for tag in tags[tag_index + 1:]:
                    start_token = tag.get('start_token')
                    if start_token >= tags[tag_index].get('start_token') + len(tokens):
                        for b_entity_index in xrange(len(tag.get('entities'))):
                            b_entity_name = graph_key_from_tag(tag, b_entity_index)
                            graph.add_edge(a_entity_name, b_entity_name)

        return graph

    def _sub_expand(self, tags):
        """This called by expand to find cliques

        Args:
            tags (list): a list of the tags used to get cliques

        Yields:
            list : list of sorted tags by start_token this is a clique
        """
        entities = {}
        graph = self._build_graph(tags)

        # name entities
        for tag in tags:
            for entity_index in xrange(len(tag.get('entities'))):
                node_name = graph_key_from_tag(tag, entity_index)
                if not node_name in entities:
                    entities[node_name] = []
                entities[node_name] += [
                    tag.get('entities', [])[entity_index],
                    tag.get('entities', [])[entity_index].get('confidence'),
                    tag
                ]

        for clique in get_cliques(list(entities), graph):
            result = []
            for entity_name in clique:
                start_token = int(entity_name.split("-")[0])
                old_tag = entities[entity_name][2]
                tag = {
                    'start_token': start_token,
                    'entities': [entities.get(entity_name)[0]],
                    'confidence': entities.get(entity_name)[1] * old_tag.get('confidence', 1.0),
                    'end_token': old_tag.get('end_token'),
                    'match': old_tag.get('entities')[0].get('match'),
                    'key': old_tag.get('entities')[0].get('key'),
                    'from_context': old_tag.get('from_context', False)
                }
                result.append(tag)
            result = sorted(result, key=lambda e: e.get('start_token'))
            yield result

    def expand(self, tags, clique_scoring_func=None):
        """This is the main function to expand tags into cliques

        Args:
            tags (list): a list of tags to find the cliques.
            clique_scoring_func (func): a function that returns a float
                value for the clique

        Returns:
            list : a list of cliques
        """
        lattice = Lattice()
        overlapping_spans = []

        def end_token_index():
            return max([t.get('end_token') for t in overlapping_spans])

        for i in xrange(len(tags)):
            tag = tags[i]

            if len(overlapping_spans) > 0 and end_token_index() >= tag.get('start_token'):
                overlapping_spans.append(tag)
            elif len(overlapping_spans) > 1:
                cliques = list(self._sub_expand(overlapping_spans))
                if clique_scoring_func:
                    cliques = sorted(cliques, key=lambda e: -1 * clique_scoring_func(e))
                lattice.append(cliques)
                overlapping_spans = [tag]
            else:
                lattice.append(overlapping_spans)
                overlapping_spans = [tag]
        if len(overlapping_spans) > 1:
            cliques = list(self._sub_expand(overlapping_spans))
            if clique_scoring_func:
                    cliques = sorted(cliques, key=lambda e: -1 * clique_scoring_func(e))
            lattice.append(cliques)
        else:
            lattice.append(overlapping_spans)

        return lattice.traverse()

