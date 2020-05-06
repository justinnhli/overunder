#!/usr/bin/env python3
"""A gradebook webapp."""

import atexit
import json
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

from overunder import GradeBook, parse_fraction

try:
    # pylint: disable = import-error
    from flask import Flask, render_template, abort, request, send_from_directory, url_for, redirect
except ModuleNotFoundError as err:

    def run_with_venv(venv):
        # type: (str) -> None
        """Run this script in a virtual environment.

        Parameters:
            venv (str): The virtual environment to use.

        Raises:
            FileNotFoundError: If the virtual environment does not exist.
            ImportError: If the virtual environment does not contain the necessary packages.
        """
        # pylint: disable = ungrouped-imports, reimported, redefined-outer-name, import-outside-toplevel
        import sys
        from os import environ, execv
        from pathlib import Path
        venv_python = Path(environ['PYTHON_VENV_HOME'], venv, 'bin', 'python3').expanduser()
        if not venv_python.exists():
            raise FileNotFoundError(f'could not find venv "{venv}" at executable {venv_python}')
        if sys.executable == str(venv_python):
            raise ImportError(f'no module {err.name} in venv "{venv}" ({venv_python})')
        execv(str(venv_python), [str(venv_python), *sys.argv])

    run_with_venv('flask-heroku')

APP = Flask(__name__)


@APP.route('/')
def root():
    # type: () -> Response
    """Respond to a Flask route."""
    return redirect(url_for('view_assignments_students', student_filter='all', assignment_filter='all'))


@APP.route('/students-assignments/<student_filter>/<assignment_filter>/')
def view_students_assignments(student_filter, assignment_filter):
    # type: (str, str) -> Response
    """Respond to a Flask route."""
    gradebook = APP.config['gradebook']
    if assignment_filter == 'all':
        assignments = list(gradebook.assignments.traversal)
    else:
        assignments = list(
            assignment for assignment in gradebook.assignments.traversal
            if assignment.qualified_name.startswith(assignment_filter)
        )
    if student_filter == 'all':
        students = list(gradebook.students.values())
    else:
        students = list(
            student for student in gradebook.students.values()
            if student.alias == student_filter
        )
    context = {
        'student_filter': student_filter,
        'assignment_filter': assignment_filter,
        'gradebook': gradebook,
        'min_depth': assignments[0].depth,
        'assignments': assignments,
        'students': students,
    }
    return render_template('students-assignments.html', **context)


@APP.route('/assignments-students/<assignment_filter>/<student_filter>/')
def view_assignments_students(assignment_filter, student_filter):
    # type: (str, str) -> Response
    """Respond to a Flask route."""
    gradebook = APP.config['gradebook']
    if assignment_filter == 'all':
        assignments = list(gradebook.assignments.traversal)
    else:
        assignments = list(
            assignment for assignment in gradebook.assignments.traversal
            if assignment.qualified_name.startswith(assignment_filter)
        )
    if student_filter == 'all':
        students = list(gradebook.students.values())
    else:
        students = list(
            student for student in gradebook.students.values()
            if student.alias == student_filter
        )
    context = {
        'assignment_filter': assignment_filter,
        'student_filter': student_filter,
        'gradebook': gradebook,
        'min_depth': assignments[0].depth,
        'assignments': assignments,
        'students': students,
    }
    return render_template('assignments-students.html', **context)


@APP.route('/save')
def save():
    # type: () -> Response
    """Save the GradeBook to file."""
    APP.config['gradebook'].write_csv()
    return redirect(request.referrer)


@APP.route('/reload')
def reload():
    # type: () -> Response
    """Respond to a Flask route."""
    APP.config['gradebook'] = GradeBook(APP.config['gradebook'].csv_path)
    return redirect(request.referrer)


@APP.route('/move-up/<qualified_name>')
def move_up(qualified_name):
    # type: (str) -> Response
    """Respond to a Flask route."""
    APP.config['gradebook'].move_assignment_up(qualified_name)
    return redirect(request.referrer)


@APP.route('/move-down/<qualified_name>')
def move_down(qualified_name):
    # type: (str) -> Response
    """Respond to a Flask route."""
    APP.config['gradebook'].move_assignment_down(qualified_name)
    return redirect(request.referrer)


@APP.route('/create-child', methods=['POST'])
def create_child():
    # type: () -> Response
    """Respond to a Flask route."""
    data = json.loads(request.get_data())
    APP.config['gradebook'].add_assignment(data['qualified_name'].strip(), data['weight_str'].strip())
    return redirect(request.referrer)


@APP.route('/delete/<qualified_name>')
def delete(qualified_name):
    # type: (str) -> Response
    """Respond to a Flask route."""
    APP.config['gradebook'].remove_assignment(qualified_name)
    return redirect(request.referrer)


@APP.route('/update_score', methods=['POST'])
def update_score():
    # type: () -> Response
    """Respond to a Flask route."""
    data = json.loads(request.get_data())
    grade = APP.config['gradebook'].get_grade(data['alias'], data['assignment'])
    if grade.display_str == data['value']:
        return json.dumps([])
    try:
        parse_fraction(data['value'])
    except ValueError:
        return abort(500)
    grade.set_grade(data['value'])
    APP.config['changed'] = True
    result = []
    while grade is not None:
        result.append({
            'qname': f'{data["alias"]}__{grade.qualified_name}',
            'display': grade.display_str,
            'projection': grade.projection_str,
            'color': grade.as_color,
        })
        grade = grade.parent
    return json.dumps(result)


@APP.route('/static/css/<filename>')
def get_css(filename):
    # type: (str) -> Response
    """Serve CSS files."""
    file_dir = APP.config['root_directory'].joinpath('static', 'css')
    file_path = file_dir.joinpath(filename)
    if file_path.exists():
        return send_from_directory(str(file_dir), filename)
    else:
        return abort(404)


@APP.route('/static/js/<filename>')
def get_js(filename):
    # type: (str) -> Response
    """Serve JavaScript files."""
    file_dir = APP.config['root_directory'].joinpath('static', 'js')
    file_path = file_dir.joinpath(filename)
    if file_path.exists():
        return send_from_directory(str(file_dir), filename)
    else:
        return abort(404)


def save_backup():
    # type: () -> None
    """Save the GradeBook to a timestamped backup."""
    gradebook = APP.config['gradebook']
    csv_name = gradebook.csv_path.name
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    gradebook.write_csv(filename=f'{csv_name}.{timestamp}.bak')


def configure_app(filepath):
    # type: (Path) -> None
    """Configure the app."""
    APP.config['gradebook'] = GradeBook(filepath)
    APP.config['root_directory'] = Path(__file__).parent.resolve()
    # The changed flag is necessary because, if Flask is run in debug
    # mode, two copies of the app will be created in separate threads.
    # This allows Flask to restart itself if the source has changed (see
    # https://stackoverflow.com/q/25504149). The problem is that only
    # *one* of those copies is updated with new data, specifically the
    # copy in the child thread. This means that when write_on_exit() is
    # called in both threads, the parent and child could clobber each
    # other. (In practice, the parent always writes second, thus wiping
    # any changes; this is likely because the parent is waiting for the
    # child to finish.) The official way of telling them apart is by
    # calling werkzeug.serving.is_running_from_reloader(); unfortunately,
    # since it's the child that has the changes, the correct value depends
    # on whether we are in debug mode (True if so, False otherwise). It's
    # therefore much cleaner to just check whether there were changes
    # ourselves, and only write if the grades have changed.
    APP.config['changed'] = False


def write_on_exit():
    if APP.config['changed']:
        APP.config['gradebook'].write_csv()


def main():
    # type: () -> None
    """Start the app."""
    arg_parser = ArgumentParser()
    arg_parser.add_argument('grades_file', type=Path, help='The grades CSV file.')
    arg_parser.add_argument('--backup', default=False, help='Backup the grades file before launching')
    args = arg_parser.parse_args()
    configure_app(args.grades_file)
    if args.backup:
        save_backup()
    atexit.register(write_on_exit)
    APP.run()


if __name__ == '__main__':
    main()
