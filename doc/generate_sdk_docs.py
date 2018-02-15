# Copyright 2017 Mycroft AI Inc.
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
import os
import pdoc


DOCS_NAME = "mycroft-skills-sdk"

DOC_OUTPUT_DIR = "build/doc/%s/html" % DOCS_NAME

documented_sdk_modules = [
    "mycroft.configuration",
    "mycroft.dialog",
    "mycroft.filesystem",
    "mycroft.session",
    "mycroft.util",
    "mycroft.util.log"
]


def module_to_docpath(module_name):
    module_source_dir = module_name.replace(".", "/")
    module_doc_dir = os.path.join(DOC_OUTPUT_DIR, module_source_dir)
    base_module_name = os.path.basename(module_doc_dir)
    if not os.path.isdir(module_source_dir):
        d = os.path.dirname(module_doc_dir)
        try:
            os.makedirs(d)
        except OSError:
            pass
        return os.path.join(d, base_module_name + '.m.html')
    else:
        try:
            os.makedirs(module_doc_dir)
        except OSError:
            pass
        return os.path.join(module_doc_dir, 'index.html')


def main():
    for m in documented_sdk_modules:
        html = pdoc.html(m, allsubmodules=True)
        with open(module_to_docpath(m), 'w') as f:
            f.write(html)
    import mycroft
    mycroft.__all__ = [m[8:] for m in documented_sdk_modules]
    root_module = pdoc.Module(mycroft)
    html = root_module.html(external_links=False, link_prefix='', source=True)
    with open(module_to_docpath("mycroft"), 'w') as f:
        f.write(html)


if __name__ == "__main__":
    main()
