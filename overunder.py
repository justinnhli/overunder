#!/usr/bin/env python3

from argparse import ArgumentParser
from pathlib import Path

from overunderlib import student_from_str


def do_init():
    """Initialize an Over/Under CSV file."""
    arg_parser = ArgumentParser()
    arg_parser.add_argument('action', nargs=1)
    arg_parser.add_argument('filepath', type=Path)
    arg_parser.add_argument('course_name')
    args = arg_parser.parse_args()
    args.filepath = args.filepath.expanduser().resolve()
    students = []
    with args.filepath.open() as fd:
        for line in fd:
            students.append(student_from_str(line.strip()))
    print('\t'.join(['Student', args.course_name]))
    for student in students:
        print(f'{student.last_name}, {student.first_name} <{student.email}>\tNone')


def do_app():
    """Start the app."""
    from app import app
    app.run(debug=True)
    

def main():
    actions = tuple(
        name[3:] for name, value in globals().items()
        if name.startswith('do_') and callable(value)
    )
    arg_parser = ArgumentParser()
    arg_parser.add_argument('action', choices=actions)
    arg_parser.add_argument('args', nargs='*')
    args = arg_parser.parse_args()
    globals()[f'do_{args.action}']()


if __name__ == '__main__':
    main()
