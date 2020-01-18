import sys
import json
from pathlib import Path

from overunderlib import GradeBook


try:
    # pylint: disable = import-error
    from flask import Flask, render_template, abort, request, send_from_directory, url_for, redirect
    from flask.json import jsonify
except ModuleNotFoundError as err:

    def run_with_venv(venv):
        """Run this script in a virtual environment.

        Parameters:
            venv (str): The virtual environment to use.
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


def create_app(filepath):
    app = Flask(__name__)
    app.config['gradebook'] = GradeBook(filepath)
    app.config['root_directory'] = Path(__file__).parent.resolve()
    return app


app = create_app(Path(sys.argv[2]))
 

@app.route('/students-assignments/<email>/<assignment_name>')
def view_students_assignments(email, assignment_name):
    gradebook = app.config['gradebook']
    if assignment_name == 'all':
        assignments = list(gradebook.assignments.traversal())
    else:
        assignments = list(
            assignment for assignment in gradebook.assignments.traversal()
            if assignment.qualified_name.startswith(assignment_name)
        )
    if email == 'all':
        students = list(gradebook.grades.keys())
    else:
        students = list(
            student for student in gradebook.grades.keys()
            if email in student
        )
    context = {
        'email': email,
        'assignment_name': assignment_name,
        'gradebook': gradebook,
        'assignments': assignments,
        'students': students,
    }
    return render_template('students-assignments.html', **context)


@app.route('/assignments-students/<assignment_name>/<email>')
def view_assignments_students(assignment_name, email):
    gradebook = app.config['gradebook']
    if assignment_name == 'all':
        assignments = list(gradebook.assignments.traversal())
    else:
        assignments = list(
            assignment for assignment in gradebook.assignments.traversal()
            if assignment.qualified_name.startswith(assignment_name)
        )
    if email == 'all':
        students = list(gradebook.students.values())
    else:
        students = list(
            student for student in gradebook.students.values()
            if student.email == email
        )
    context = {
        'assignment_name': assignment_name,
        'email': email,
        'gradebook': gradebook,
        'assignments': assignments,
        'students': students,
    }
    return render_template('assignments-students.html', **context)


@app.route('/save_score', methods=['POST'])
def save_score():
    data = json.loads(request.get_data())
    gradebook = app.config['gradebook']
    email = data['email'].replace('_', '@')
    changed_grades = [gradebook.get(gradebook.students[email], data['assignment'])]
    while changed_grades[-1].parent is not None:
        changed_grades.append(changed_grades[-1].parent)
    result = [ 
        [f'{email}|{grade.qualified_name}', grade.display_str]
        for grade in changed_grades
    ]
    return json.dumps(result)


@app.route('/static/css/<filename>')
def get_css(filename):
    """Serve CSS files."""
    file_dir = app.config['root_directory'].joinpath('static', 'css')
    file_path = file_dir.joinpath(filename)
    if file_path.exists():
        return send_from_directory(str(file_dir), filename)
    else:
        return abort(404)


@app.route('/static/js/<filename>')
def get_js(filename):
    """Serve JavaScript files."""
    file_dir = app.config['root_directory'].joinpath('static', 'js')
    file_path = file_dir.joinpath(filename)
    if file_path.exists():
        return send_from_directory(str(file_dir), filename)
    else:
        return abort(404)
