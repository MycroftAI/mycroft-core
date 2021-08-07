import os.path
from functools import wraps
from importlib import import_module
from inspect import signature
from sys import version
from warnings import warn

from lingua_franca import config

_SUPPORTED_LANGUAGES = ("ca", "cs", "da", "de", "en", "es", "fr", "hu",
                        "it", "nl", "pl", "pt", "sl", "sv", "fa")

_SUPPORTED_FULL_LOCALIZATIONS = ("ca-es", "cs-cz", "da-dk", "de-de",
                                 "en-au", "en-us", "es-es", "fr-fr",
                                 "hu-hu", "it-it", "nl-nl", "pl-pl",
                                 "fa-ir", "pt-pt", "ru-ru", "sl-si",
                                 "sv-se", "tr-tr")

_DEFAULT_FULL_LANG_CODES = {'ca': 'ca-es',
                            'cs': 'cs-cz',
                            'da': 'da-dk',
                            'de': 'de-de',
                            'en': 'en-us',
                            'es': 'es-es',
                            'fa': 'fa-ir',
                            'fr': 'fr-fr',
                            'hu': 'hu-hu',
                            'it': 'it-it',
                            'nl': 'nl-nl',
                            'pl': 'pl-pl',
                            'pt': 'pt-pt',
                            'ru': 'ru-ru',
                            'sl': 'sl-si',
                            'sv': 'sv-se',
                            'tr': 'tr-tr'}

__default_lang = None
__active_lang_code = None
__loaded_langs = []

_localized_functions = {}

# TODO the deprecation of 'lang=None' and 'lang=<invalid>' can refer to
# commit 35efd0661a178e82f6745ad17e10e607c0d83472 for the "proper" state
# of affairs, raising the errors below instead of deprecation warnings

# Once the deprecation is complete, functions which have had their default
# parameter changed from lang=None to lang='' should be switched back


class UnsupportedLanguageError(NotImplementedError):
    pass


class FunctionNotLocalizedError(NotImplementedError):
    pass


NoneLangWarning = \
    DeprecationWarning("Lingua Franca is dropping support"
                       " for 'lang=None' as an explicit"
                       " argument.")
InvalidLangWarning = \
    DeprecationWarning("Invalid language code detected. Falling back on "
                       "default.\nThis behavior is deprecated. The 'lang' "
                       "parameter is optional, and only accepts supported "
                       "language codes, beginning with Lingua Franca 0.3.0")


def _raise_unsupported_language(language):
    """
    Raise an error when a language is unsupported

    Arguments:
        language: str
            The language that was supplied.
    """
    supported = ' '.join(_SUPPORTED_LANGUAGES)
    raise UnsupportedLanguageError("\nLanguage '{language}' is not yet "
                                   "supported by Lingua Franca. "
                                   "Supported language codes "
                                   "include the following:\n{supported}"
                                   .format(language=language, supported=supported))


def get_supported_langs():
    """
    Returns:
        list(str)
    """
    return _SUPPORTED_LANGUAGES


def get_active_langs():
    """ Get the list of currently-loaded language codes

    Returns:
        list(str)
    """
    return __loaded_langs


def _set_active_langs(langs=None, override_default=True):
    """ Set the list of languages to load.
        Unloads previously-loaded languages which are not specified here.
        If the input list does not contain the current default language,
        langs[0] will become the new default language. This behavior
        can be overridden.

    Arguments:
        langs: {list(str) or str} -- a list of language codes to load

    Keyword Arguments:
        override_default (bool) -- Change default language to first entry if
                                    the current default is no longer present
                                    (default: True)
    """
    if isinstance(langs, str):
        langs = [langs]
    if not isinstance(langs, list):
        raise(TypeError("lingua_franca.internal._set_active_langs expects"
                        " 'str' or 'list'"))
    global __loaded_langs, __default_lang
    __loaded_langs = list(dict.fromkeys(langs))
    if __default_lang:
        if override_default or get_primary_lang_code(__default_lang) \
                not in __loaded_langs:
            if len(__loaded_langs):
                set_default_lang(get_full_lang_code(__loaded_langs[0]))
            else:
                __default_lang = None
    _refresh_function_dict()


def _refresh_function_dict():
    for mod in _localized_functions.keys():
        populate_localized_function_dict(mod, langs=__loaded_langs)


def is_supported_lang(lang):
    try:
        return lang.lower() in _SUPPORTED_LANGUAGES
    except AttributeError:
        return False


def is_supported_full_lang(lang):
    """
    Arguments:
        lang (str): a full language code, such as "en-US" (case insensitive)

    Returns:
        bool - does Lingua Franca support this language code?
    """
    try:
        return lang.lower() in _SUPPORTED_FULL_LOCALIZATIONS
    except AttributeError:
        return False


def load_language(lang):
    """Load `lang` and its functions into memory. Will only import those
       functions which belong to a loaded module. In other words, if you have
       lingua_franca.parse loaded, but *not* lingua_franca.format,
       running `load_language('es') will only import the Spanish-language
       parsers, and not the formatters.

       The reverse is also true: importing a module, such as
       `import lingua_franca.parse`, will only import those functions
       which belong to currently-loaded languages.

    Arguments:
        lang (str): the language code to load (any supported lang code,
                    whether 'primary' or 'full')
                    Case-insensitive.
    """
    if not isinstance(lang, str):
        raise TypeError("lingua_franca.load_language expects 'str' "
                        "(got " + type(lang) + ")")
    if lang not in _SUPPORTED_LANGUAGES:
        if lang in _SUPPORTED_FULL_LOCALIZATIONS:
            lang = get_primary_lang_code(lang)
    if lang not in __loaded_langs:
        __loaded_langs.append(lang)
    if not __default_lang:
        set_default_lang(lang)
    _set_active_langs(__loaded_langs)


def load_languages(langs):
    """Load multiple languages at once
       Simple for loop using load_language()

    Args:
        langs (list[str])
    """
    for lang in langs:
        load_language(lang)


def unload_language(lang):
    """Opposite of load_language()
       Unloading the default causes the next language in
       `lingua_franca.get_active_langs()` to become the default.

       Will not stop you from unloading the last language, as this may be
       desirable for some applications.

    Args:
        lang (str): language code to unload
    """
    if lang in __loaded_langs:
        __loaded_langs.remove(lang)
        _set_active_langs(__loaded_langs)


def unload_languages(langs):
    """Opposite of load_languages()
       Simple for loop using unload_language()

    Args:
        langs (list[str])
    """
    for lang in langs:
        __loaded_langs.remove(lang)
    _set_active_langs(__loaded_langs)


def get_default_lang():
    """ Return the current default language.
        This returns the active BCP-47 code, such as 'en' or 'es'.
        For the current localization/full language code,
        such as 'en-US' or 'es-ES', call `get_default_loc()`

        See:
            https://en.wikipedia.org/wiki/IETF_language_tag

    Returns:
        str: A primary language code, e.g. ("en", or "pt")
    """
    return __default_lang


def get_default_loc():
    """ Return the current, localized BCP-47 language code, such as 'en-US'
        or 'es-ES'. For the default language *family* - which is passed to
        most parsers and formatters - call `get_default_lang`

        The 'localized' portion conforms to ISO 3166-1 alpha-2
        https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
    """
    return __active_lang_code


def set_default_lang(lang_code):
    """ Set the active BCP-47 language code to be used in formatting/parsing
        Will choose a default localization if passed a primary language family
        (ex: `set_default_lang("en")` will default to "en-US")

        Will respect localization when passed a full lang code.

        For more information about valid lang codes, see get_default_lang()
        and get_default_loc()

    Args:
        lang(str): BCP-47 language code, e.g. "en-us" or "es-mx"
    """
    global __default_lang, __active_lang_code

    lang_code = lang_code.lower()
    primary_lang_code = get_primary_lang_code(lang_code)
    if primary_lang_code not in _SUPPORTED_LANGUAGES:
        _raise_unsupported_language(lang_code)
    else:
        __default_lang = primary_lang_code

    # make sure the default language is loaded.
    # also make sure the default language is at the front.
    # position doesn't matter here, but it clarifies things while debugging.
    if __default_lang in __loaded_langs:
        __loaded_langs.remove(__default_lang)
    __loaded_langs.insert(0, __default_lang)
    _refresh_function_dict()

    if is_supported_full_lang(lang_code):
        __active_lang_code = lang_code
    else:
        __active_lang_code = get_full_lang_code(__default_lang)

# TODO remove this when invalid lang codes are removed (currently deprecated)


def get_primary_lang_code(lang=''):
    if not lang:
        if lang is None:
            warn(NoneLangWarning)
        lang = get_default_loc()
    # if not (lang):
    try:
        lang = __get_primary_lang_code_deprecation_warning(lang)
    except UnsupportedLanguageError:
        warn(InvalidLangWarning)
        lang = get_default_loc()
    return lang


def __get_primary_lang_code_deprecation_warning(lang=''):
    """ Get the primary language code

    Args:
        lang(str, optional): A BCP-47 language code
                              (If omitted, equivalent to
                              `lingua_franca.get_default_lang()`)

    Returns:
        str: A primary language family, such as "en", "de" or "pt"
    """
    # split on the hyphen and only return the primary-language code
    # NOTE: This is typically a two character code.  The standard allows
    #       1, 2, 3 and 4 character codes.  In the future we can consider
    #       mapping from the 3 to 2 character codes, for example.  But for
    #       now we can just be careful in use.
    if not lang:
        return get_default_lang()
    elif not isinstance(lang, str):
        raise(TypeError("lingua_franca.get_primary_lang_code() expects"
                        " an (optional)argument of type 'str', but got " +
                        type(lang)))
    else:
        lang_code = lang.lower()
    if lang_code not in _SUPPORTED_FULL_LOCALIZATIONS and lang_code not in \
            _SUPPORTED_LANGUAGES:
        # We don't know this language code. Check if the input is
        # formatted like a language code.
        if lang == (("-".join([lang[:2], lang[3:]]) or None)):
            warn("Unrecognized language code: '" + lang + "', but it appears "
                 "to be a valid language code. Returning the first two chars.")
            return lang_code.split("-")[0]
        else:
            raise(ValueError("Invalid input: " + lang))
    return lang_code.split("-")[0]

# TODO remove this when invalid lang codes are removed (currently deprecated)


def get_full_lang_code(lang=''):
    if not lang:
        if lang is None:
            warn(NoneLangWarning)
        lang = get_default_loc()
    if not is_supported_full_lang(lang):
        try:
            lang = __get_full_lang_code_deprecation_warning(lang)
        except UnsupportedLanguageError:
            warn(InvalidLangWarning)
            lang = get_default_loc()
    return lang


def __get_full_lang_code_deprecation_warning(lang=''):
    """ Get the full language code

    Args:
        lang(str, optional): A BCP-47 language code
                              (if omitted, equivalent to
                               `lingua_franca.get_default_loc()`)

    Returns:
        str: A full language code, such as "en-us" or "de-de"
    """
    if lang is None:
        return __active_lang_code.lower()
    elif not isinstance(lang, str):
        raise TypeError("get_full_lang_code expects str, "
                        "got {}".format(type(lang)))
    if lang.lower() in _SUPPORTED_FULL_LOCALIZATIONS:
        return lang
    elif lang in _DEFAULT_FULL_LANG_CODES:
        return _DEFAULT_FULL_LANG_CODES[lang]
    else:
        raise UnsupportedLanguageError(lang)


def localized_function(run_own_code_on=[type(None)]):
    """
    Decorator which finds localized functions, and calls them, from signatures
    defined in the top-level modules. See lingua_franca.format or .parse for
    examples of the decorator in action.

    Note that, by default, wrapped functions will never actually be executed.
    Rather, when they're called, their arguments will be passed directly to
    their localized equivalent, specified by the 'lang' parameter.

    The wrapper can be instructed to execute the wrapped function itself when
    a specified error is raised (see the argument 'run_own_code_on')

    For instance, this decorator wraps parse.extract_number(), which has no
    logic of its own. A call to

        extract_number('uno', lang='es')

    will locate and call

        lingua_franca.lang.parse_es.extract_number_es('uno')

    By contrast, here's the decorator above format.nice_number, with the param:

        @localized_function(run_own_code_on=[UnsupportedLanguageError])
        def nice_number(number, lang='', speech=True, denominators=None):

    Here, nice_number() itself will be executed in the event that the localizer
    raises an UnsupportedLanguageError.

    Arguments:
        run_own_code_on(list(type), optional)
            A list of Error types (ValueError, NotImplementedError, etc)
            which, if they are raised, will trigger the wrapped function's
            own code.

            If this argument is omitted, the function itself will never
            be run. Calls to the wrapped function will be passed to the
            appropriate, localized function.


    """
    # Make sure everything in run_own_code_on is an Error or None
    BadTypeError = \
        ValueError("@localized_function(run_own_code_on=<>) expected an "
                   "Error type, or a list of Error types. Instead, it "
                   "received this value:\n" + str(run_own_code_on))
    # TODO deprecate these kwarg values 6-12 months after v0.3.0 releases

    if run_own_code_on != [None]:
        def is_error_type(_type):
            if not callable(_type):
                return False
            _instance = _type()
            rval = isinstance(_instance, BaseException) if _instance else True
            del _instance
            return rval
        if not isinstance(run_own_code_on, list):
            try:
                run_own_code_on = list(run_own_code_on)
            except TypeError:
                raise BadTypeError
        if not all((is_error_type(e) for e in run_own_code_on)):
            raise BadTypeError

    # Begin wrapper
    def localized_function_decorator(func):
        # Wrapper's logic
        def _call_localized_function(func, *args, **kwargs):
            lang_code = None
            load_langs_on_demand = config.load_langs_on_demand
            unload_language_afterward = False
            func_signature = signature(func)
            func_params = list(func_signature.parameters)
            lang_param_index = func_params.index('lang')
            full_lang_code = None

            # Check if we're passing a lang as a kwarg
            if 'lang' in kwargs.keys():
                lang_param = kwargs['lang']
                if lang_param == None:
                    warn(NoneLangWarning)
                    lang_code = get_default_lang()
                else:
                    lang_code = lang_param

            # Check if we're passing a lang as a positional arg
            elif lang_param_index < len(args):
                lang_param = args[lang_param_index]
                if lang_param == None:
                    warn(NoneLangWarning)
                    lang_code = get_default_lang()
                elif lang_param in _SUPPORTED_LANGUAGES or \
                        lang_param in _SUPPORTED_FULL_LOCALIZATIONS:
                    lang_code = args[lang_param_index]
                args = args[:lang_param_index] + args[lang_param_index+1:]

            # Turns out, we aren't passing a lang code at all
            lang_code = lang_code or get_default_lang()
            if not lang_code:
                if load_langs_on_demand:
                    raise ModuleNotFoundError("No language module loaded "
                                              "and none specified.")
                else:
                    raise ModuleNotFoundError("No language module loaded.")

            if lang_code not in _SUPPORTED_LANGUAGES:
                try:
                    tmp = lang_code
                    __use_tmp = True
                    lang_code = get_primary_lang_code(lang_code)
                except ValueError:
                    __error = \
                        UnsupportedLanguageError("\nLanguage '{language}' is not yet "
                                                 "supported by Lingua Franca. "
                                                 "Supported language codes "
                                                 "include the following:\n{supported}"
                                                 .format(
                                                     language=lang_code,
                                                     supported=_SUPPORTED_FULL_LOCALIZATIONS))
                    if UnsupportedLanguageError in run_own_code_on:
                        raise __error
                    else:
                        warn(DeprecationWarning("The following warning will "
                                                "become an exception in a future "
                                                "version of Lingua Franca." +
                                                str(__error)))
                        lang_code = get_default_lang()
                        full_lang_code = get_full_lang_code()
                        __use_tmp = False
                if lang_code not in _SUPPORTED_LANGUAGES:
                    _raise_unsupported_language(lang_code)
                if __use_tmp:
                    full_lang_code = tmp
            else:
                full_lang_code = get_full_lang_code(lang_code)

            # Here comes the ugly business.
            _module_name = func.__module__.split('.')[-1]
            _module = import_module(".lang." + _module_name +
                                    "_" + lang_code, "lingua_franca")
            # The nonsense above gets you from lingua_franca.parse
            # to lingua_franca.lang.parse_xx
            if _module_name not in _localized_functions.keys():
                raise ModuleNotFoundError("Module lingua_franca." +
                                          _module_name + " not recognized")
            if lang_code not in _localized_functions[_module_name].keys():
                if load_langs_on_demand:
                    load_language(lang_code)
                    unload_language_afterward = True
                else:
                    raise ModuleNotFoundError(_module_name +
                                              " module of language '" +
                                              lang_code +
                                              "' is not currently loaded.")
            func_name = func.__name__.split('.')[-1]
            # At some point in the past, both the module and the language
            # were imported/loaded, respectively.
            # When that happened, we cached the *signature* of each
            # localized function.
            #
            # This is the crucial element that allows us to import funcs
            # on the fly.
            #
            # If we didn't find a localized function to correspond with
            # the wrapped function, we cached NotImplementedError in its
            # place.
            loc_signature = _localized_functions[_module_name][lang_code][func_name]
            if isinstance(loc_signature, type(NotImplementedError())):
                raise loc_signature

            # Now we have the appropriate localized module. Let's get
            # the localized function.
            try:
                localized_func = getattr(
                    _module, func_name + "_" + lang_code)
            except AttributeError:
                raise FunctionNotLocalizedError(func_name, lang_code)

            # We now have a localized function, such as
            # lingua_franca.parse.extract_datetime_en
            # Get 'lang' out of its parameters.
            if 'lang' in kwargs:
                del kwargs['lang']
            args = tuple(arg for arg in list(args) if
                         arg not in (lang_code, full_lang_code))

            # Now we call the function, ignoring any kwargs from the
            # wrapped function that aren't in the localized function.
            r_val = localized_func(*args,
                                   **{arg: val for arg, val
                                      in kwargs.items()
                                      if arg in loc_signature.parameters})

            # Unload all the stuff we just assembled and imported
            del localized_func
            del _module
            if unload_language_afterward:
                unload_language(lang_code)
            return r_val

        # Actual wrapper
        @wraps(func)
        def call_localized_function(*args, **kwargs):
            if run_own_code_on != [type(None)]:
                try:
                    return _call_localized_function(func, *args, **kwargs)
                except Exception as e:  # Intercept, check for run_own_code_on
                    if any((isinstance(e, error) for error in run_own_code_on)):
                        return func(*args, **kwargs)
                    else:
                        raise e
            else:  # don't intercept any exceptions
                return _call_localized_function(func, *args, **kwargs)
        return call_localized_function
    try:
        return localized_function_decorator
    except NotImplementedError as e:
        warn(str(e))
        return


def populate_localized_function_dict(lf_module, langs=get_active_langs()):
    """Returns a dictionary of dictionaries, containing localized functions.

    Used by the top-level modules to locate, cache, and call localized funcs.

    Arguments:
        lf_module(str) - - the name of the top-level module

    Returns:
        Dict - - {language_code: {function_name(str): function}}

    Note:
        The dictionary returned can be used directly,
        but it's normally discarded. Rather, this function will create
        the dictionary as a member of
        `lingua_franca.internal._localized_functions`,
        and its members are invoked via the `@localized_function` decorator.

    Example:
        populate_localized_function_dict("format")["en"]["pronounce_number"](1)
        "one"
    """
    bad_lang_code = "Language code '{}' is registered with" \
        " Lingua Franca, but its " + lf_module + " module" \
        " could not be found."
    return_dict = {}
    for lang_code in langs:
        primary_lang_code = get_primary_lang_code(lang_code)
        return_dict[primary_lang_code] = {}
        _FUNCTION_NOT_FOUND = ""
        try:
            lang_common_data = import_module(".lang.common_data_" + primary_lang_code,
                                             "lingua_franca")
            _FUNCTION_NOT_FOUND = getattr(lang_common_data,
                                          "_FUNCTION_NOT_IMPLEMENTED_WARNING")
            del lang_common_data
        except Exception:
            _FUNCTION_NOT_FOUND = "This function has not been implemented" \
                " in the specified language."
        _FUNCTION_NOT_FOUND = FunctionNotLocalizedError(_FUNCTION_NOT_FOUND)

        try:
            mod = import_module(".lang." + lf_module + "_" + primary_lang_code,
                                "lingua_franca")
        except ModuleNotFoundError:
            warn(Warning(bad_lang_code.format(primary_lang_code)))
            continue

        function_names = getattr(import_module("." + lf_module, "lingua_franca"),
                                 "_REGISTERED_FUNCTIONS")
        for function_name in function_names:
            try:
                function = getattr(mod, function_name
                                   + "_" + primary_lang_code)
                function_signature = signature(function)
                del function
            except AttributeError:
                function_signature = _FUNCTION_NOT_FOUND
                # TODO log these occurrences: "function 'function_name' not
                # implemented in language 'primary_lang_code'"
                #
                # Perhaps provide this info to autodocs, to help volunteers
                # identify the functions in need of localization
            return_dict[primary_lang_code][function_name] = function_signature

        del mod
    _localized_functions[lf_module] = return_dict
    return _localized_functions[lf_module]


def resolve_resource_file(res_name, data_dir=None):
    """Convert a resource into an absolute filename.

    Resource names are in the form: 'filename.ext'
    or 'path/filename.ext'

    The system wil look for ~/.mycroft/res_name first, and
    if not found will look at / opt/mycroft/res_name,
    then finally it will look for res_name in the 'mycroft/res'
    folder of the source code package.

    Example:
    With mycroft running as the user 'bob', if you called
        resolve_resource_file('snd/beep.wav')
    it would return either '/home/bob/.mycroft/snd/beep.wav' or
    '/opt/mycroft/snd/beep.wav' or '.../mycroft/res/snd/beep.wav',
    where the '...' is replaced by the path where the package has
    been installed.

    Args:
        res_name(str): a resource path/name
    Returns:
        str: path to resource or None if no resource found
    """
    # First look for fully qualified file (e.g. a user setting)
    if os.path.isfile(res_name):
        return res_name

    # Now look for ~/.mycroft/res_name (in user folder)
    filename = os.path.expanduser("~/.mycroft/" + res_name)
    if os.path.isfile(filename):
        return filename

    # Next look for /opt/mycroft/res/res_name
    data_dir = data_dir or os.path.expanduser("/opt/mycroft/res/")
    filename = os.path.expanduser(os.path.join(data_dir, res_name))
    if os.path.isfile(filename):
        return filename

    # Finally look for it in the source package
    filename = os.path.join(os.path.dirname(__file__), 'res', res_name)
    filename = os.path.abspath(os.path.normpath(filename))
    if os.path.isfile(filename):
        return filename

    return None  # Resource cannot be resolved


def lookup_variant(mappings, key="variant"):
    """function decorator
    maps strings to Enums expected by language specific functions
    mappings can be used to translate values read from configuration files

    Example usage:

        @lookup_variant({
            "default": TimeVariant.DEFAULT,
            "traditional": TimeVariant.TRADITIONAL
        })
        def nice_time_XX(dt, speech=True, use_24hour=False, use_ampm=False,
                         variant=None):
            variant = variant or TimeVariant.DEFAULT
            (...)

    """
    if not isinstance(mappings, dict):
        raise ValueError

    # Begin wrapper
    def lang_variant_function_decorator(func):

        @wraps(func)
        def call_function(*args, **kwargs):
            if key in kwargs and isinstance(kwargs[key], str):
                if kwargs[key] in mappings:
                    kwargs[key] = mappings[kwargs[key]]
                else:
                    raise ValueError("Unknown variant, mapping does not "
                                     "exist for {v}".format(v=key))
            return func(*args, **kwargs)

        return call_function

    try:
        return lang_variant_function_decorator
    except NotImplementedError as e:
        warn(str(e))
        return
