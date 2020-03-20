import re
from collections import namedtuple, defaultdict
from csv import writer as csv_writer
from fractions import Fraction
from pathlib import Path


class Assignment:

    def __init__(self, raw_weight, name, children=None, extra_credit=False):
        self.name = name
        self.extra_credit = extra_credit
        self.parent = None
        self._depth = None
        self._qualified_name = None
        if isinstance(raw_weight, (int, float)):
            self.weight_points = Fraction(raw_weight)
            self.weight = None
            self.weight_type = 'points'
        elif isinstance(raw_weight, str) and raw_weight.endswith('%'):
            self.weight_points = Fraction(raw_weight[:-1])
            self.weight = self.weight_points / 100
            self.weight_type = 'percent'
        else:
            # TODO allow Fraction weights?
            raise ValueError(f'unknown weight type: {raw_weight}')
        if children:
            uses_points = (children[0].weight is None)
            children_total = 0
            self.children = children
            for child in self.children:
                child.parent = self
                if uses_points and child.weight is not None:
                    raise ValueError(f'{child.qualified_name} mixes points and percentages')
                if not child.extra_credit:
                    children_total += child.weight_points
            if uses_points:
                for child in self.children:
                    child.weight = Fraction(child.weight_points, children_total)
        else:
            self.children = []

    @property
    def depth(self):
        if self._depth is None:
            if self.parent is None:
                self._depth = 0
            else:
                self._depth = self.parent.depth + 1
        return self._depth

    @property
    def qualified_name(self):
        if self._qualified_name is None:
            if self.parent is None:
                self._qualified_name = self.name
            else:
                self._qualified_name = f'{self.parent.qualified_name}::{self.name}'
        return self._qualified_name

    @property
    def heading(self):
        if self.weight_type == 'points':
            weight = f'{float(self.weight_points):.2f}pts'
        elif self.weight_type == 'percent':
            weight = f'{float(self.weight):.2%}'
        else:
            raise ValueError(f'unknown weight type: {self.weight_type}')
        if self.extra_credit:
            extra_credit = '*'
        else:
            extra_credit = ''
        return f'{self.depth * "__"}{self.name}{extra_credit} ({weight})'

    def traversal(self):
        yield self
        for child in self.children:
            yield from child.traversal()

    def leaves(self):
        if self.children:
            for child in self.children:
                yield from child.leaves()
        else:
            yield self

    def to_headings(self):
        return [assignment.heading for assignment in self.traversal()]

    def grade(self, student, scores):
        scores = list(scores)
        num_scores = len(scores)
        num_leaves = len(list(self.traversal()))
        if num_scores != num_leaves:
            raise ValueError(' '.join([
                f'Assignment {self.qualified_name} has {num_leaves} leaves',
                f'but {num_scores} scores were given',
            ]))
        return self._grade(student, (score for score in scores))

    def _grade(self, student, scores):
        score = next(scores)
        if not self.children:
            return Grade(student, self, score)
        else:
            children = [child._grade(student, scores) for child in self.children]
            return Grade(student, self, score, children)

    @staticmethod
    def from_strings(strings):
        StackFrame = namedtuple('StackFrame', 'raw_weight, name, extra_credit, children')
        regex = r'(?P<indent>(__)*)(?P<name>[^*]*)(?P<extra>\*?) \((?P<raw_weight>[^)]*)\)'
        prev_depth = -1
        stack = []
        for string in strings:
            match = re.fullmatch(regex, string)
            depth = len(match.group('indent')) / 2
            name = match.group('name')
            extra_credit = bool(match.group('extra'))
            raw_weight = match.group('raw_weight')
            if raw_weight.endswith('pts'):
                raw_weight = float(raw_weight[:-3])
            while prev_depth >= depth:
                stack[-2].children.append(Assignment(**stack[-1]._asdict()))
                stack.pop(-1)
                prev_depth -= 1
            stack.append(StackFrame(raw_weight, name, extra_credit, []))
            prev_depth = depth
        while len(stack) > 1:
            stack[-2].children.append(Assignment(**stack[-1]._asdict()))
            stack.pop(-1)
        return Assignment(**stack[0]._asdict())


class Grade:

    def __init__(self, student, assignment, raw_score_str, children=None):
        self.student = student
        self.assignment = assignment

        self.parent = None
        if children is None:
            self.children = []
        else:
            self.children = children
            for child in self.children:
                child.parent = self

        self.raw_score_str = raw_score_str
        self.score_type = None
        self._percent = None
        self.update()

    def __getitem__(self, key):
        # FIXME make recursion nicer
        if isinstance(key, str):
            return self[key.split('::')]
        if key[0] != self.name:
            raise KeyError(key)
        if len(key) == 1:
            return self
        for child in self.children:
            if child.name == key[1]:
                return child[key[1:]]
        raise KeyError(key)

    def __contains__(self, key):
        try:
            return self[key] is not None
        except KeyError:
            return False

    def set(self, raw_score_str):
        self.raw_score_str = raw_score_str
        self.update()

    def update(self):
        if self.children:
            self._percent = None
            assert str(self.percent) == self.raw_score_str
        elif self.raw_score_str == 'None':
            self.score_type = 'none'
            self._percent = Fraction(0)
        elif self.raw_score_str.endswith('%'):
            self.score_type = 'percent'
            self._percent = Fraction(self.raw_score_str[:-1]) / 100
        else:
            assert self.weight_type != 'percent'
            self.score_type = 'points'
            self._percent = Fraction(Fraction(self.raw_score_str), self.weight_points)
        if self.parent is not None:
            self.parent.update()

    @property
    def name(self):
        return self.assignment.name

    @property
    def weight(self):
        return self.assignment.weight

    @property
    def weight_type(self):
        return self.assignment.weight_type

    @property
    def weight_points(self):
        return self.assignment.weight_points

    @property
    def total(self):
        return self.assignment.total

    @property
    def depth(self):
        return self.assignment.depth

    @property
    def qualified_name(self):
        return self.assignment.qualified_name

    @property
    def heading(self):
        return self.assignment.heading

    @property
    def percent(self):
        if self._percent is None:
            self._percent = sum(child.weight * child.percent for child in self.children)
        return self._percent

    @property
    def score(self):
        if self.raw_score_str is not None:
            return self.raw_score_str
        else:
            return str(self.percent)

    @property
    def display_str(self):
        if self.leaf:
            return self.score
        else:
            return f'{float(self._percent):.2%}'

    @property
    def leaf(self):
        return not bool(self.children)

    def traversal(self):
        yield self
        for child in self.children:
            yield from child.traversal()

    def leaves(self):
        if self.children:
            for child in self.children:
                yield from child.leaves()
        else:
            yield self


class Student(namedtuple('Student', 'first_name, last_name, email')):

    @property
    def alias(self):
        return self.email.split('@')[0]


def student_from_str(line):
    regex = r'(?P<last_name>[^,]*), (?P<first_name>.*) <(?P<email>.*)>'
    return Student(**re.fullmatch(regex, line).groupdict())


class GradeBook:

    def __init__(self, filepath):
        self.filepath = filepath
        with self.filepath.open() as fd:
            lines = fd.read().splitlines()
        assignment_strs = lines[0].split('\t')[1:]
        self.assignments = Assignment.from_strings(assignment_strs)
        assert assignment_strs == list(assignment.heading for assignment in self.assignments.traversal())
        self.students = {}
        self.grades = {}
        for line in lines[1:]:
            student_str, *scores = line.split('\t')
            student = student_from_str(student_str)
            self.grades[student.email] = self.assignments.grade(student, scores)
            self.students[student.email] = student

    def get(self, student, assignment):
        return self.grades[student.email][assignment]

    def get_student_by_email(self, email):
        return self.grades[email]

    def set(self, student, assignment, grade):
        self.grades[student.email][assignment].set(grade)

    def move_up(self, assignment):
        print('move up ' + assignment)
        pass

    def move_down(self, assignment):
        print('move down ' + assignment)
        pass

    def create_child(self, assignment, name):
        print('move down ' + assignment + ' ' + name)
        pass

    def delete(self, assignment):
        pass

    def save(self):
        self.to_csv()

    def to_csv(self, filepath=None):
        if filepath is None:
            filepath = self.filepath
        with filepath.open('w') as fd:
            fd.write('\t'.join([
                'Student',
                *(assignment.heading for assignment in self.assignments.traversal()),
            ]))
            fd.write('\n')
            for email in self.grades:
                student = self.students[email]
                fd.write('\t'.join([
                    f'{student.last_name}, {student.first_name} <{student.email}>',
                    *(
                        self.grades[email][assignment.qualified_name].score
                        for assignment in self.assignments.traversal()
                    ),
                ]))
                fd.write('\n')
