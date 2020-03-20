"""A gradebook webapp."""

import json
from pathlib import Path
from argparse import ArgumentParser

from overunder import GradeBook

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


@APP.route('/students-assignments/<student_filter>/<assignment_filter>')
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
        students = list(gradebook.grades.keys())
    else:
        students = list(
            student for student in gradebook.grades.keys()
            if student_filter in student
        )
    context = {
        'student_filter': student_filter,
        'assignment_filter': assignment_filter,
        'gradebook': gradebook,
        'assignments': assignments,
        'students': students,
    }
    return render_template('students-assignments.html', **context)


@APP.route('/assignments-students/<assignment_filter>/<student_filter>')
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
    APP.config['gradebook'].add_assignment(data['qualified_name'], data['weight_str'])
    return redirect(request.referrer)


@APP.route('/delete/<assignment_name>')
def delete(assignment_name):
    # type: (str) -> Response
    """Respond to a Flask route."""
    raise NotImplementedError()


@APP.route('/reload')
def reload():
    # type: () -> Response
    """Respond to a Flask route."""
    gradebook = APP.config['gradebook']
    APP.config['gradebook'] = GradeBook(gradebook.csv_path)
    return redirect(request.referrer)


@APP.route('/save_score', methods=['POST'])
def save_score():
    # type: () -> Response
    """Respond to a Flask route."""
    data = json.loads(request.get_data())
    gradebook = APP.config['gradebook']
    gradebook.set_grade(data['alias'], data['assignment'], data['value'])
    gradebook.write_csv()
    curr_grade = gradebook.get_grade(data['alias'], data['assignment'])
    changed_grades = []
    while curr_grade.parent is not None:
        curr_grade = curr_grade.parent
        changed_grades.append(curr_grade)
    result = [
        [f'{data["alias"]}__{grade.qualified_name}', grade.display_str]
        for grade in changed_grades
    ]
    gradebook.write_csv()
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


def configure_app(filepath):
    # type: (Path) -> None
    """Configure the app."""
    APP.config['gradebook'] = GradeBook(filepath)
    APP.config['root_directory'] = Path(__file__).parent.resolve()


def main():
    # type: () -> None
    """Start the app."""
    arg_parser = ArgumentParser()
    arg_parser.add_argument('grades_file', type=Path, help='The grades CSV file.')
    args = arg_parser.parse_args()
    configure_app(args.grades_file)
    APP.run(debug=True)


if __name__ == '__main__':
    main()
