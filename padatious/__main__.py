import inspect
import json
from os.path import basename, splitext

from argparse import ArgumentParser

from padatious import IntentContainer


def train_setup(parser):
    parser.add_argument('intent_cache', help='Folder to write trained intents to')
    parser.add_argument('input_files', nargs='*', help='Input .intent and .entity files')
    parser.add_argument('-d', '--data', help='Serialized training args', type=json.loads)
    parser.add_argument('-s', '--single-thread', help='Run training in a single thread')
    parser.add_argument('-f', '--force', help='Force retraining if already trained')
    parser.add_argument('-a', '--args', help='Extra args (list) for function', type=json.loads)
    parser.add_argument('-k', '--kwargs', help='Extra kwargs (json) for function', type=json.loads)


def train(parser, args):
    if bool(args.input_files) == bool(args.data):
        parser.error('You must specify one of input_files or --data (but not both)')

    cont = IntentContainer(args.intent_cache)
    if args.data:
        cont.apply_training_args(args.data)
    else:
        for fn in args.input_files:
            obj_name, ext = splitext(basename(fn))
            if ext == '.intent':
                cont.load_intent(obj_name, fn)
            elif ext == '.entity':
                cont.load_entity(obj_name, fn)
            else:
                parser.error('Unknown file extension: {}'.format(ext))
    kwargs = inspect.signature(cont.train).bind(*(args.args or [])).arguments
    kwargs.update(args.kwargs or {})
    kwargs.setdefault('debug', True)
    kwargs.setdefault('single_thread', args.single_thread)
    kwargs.setdefault('force', args.force)
    if cont.train(**kwargs):
        return 0
    return 10  # timeout


def main():
    parser = ArgumentParser(description='Tool to interact with padatious via command line')
    p = parser.add_subparsers(dest='action')
    p.required = True
    train_setup(p.add_parser('train'))

    args = parser.parse_args()
    if args.action == 'train':
        exit(train(parser, args))


if __name__ == '__main__':
    main()
