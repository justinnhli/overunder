import re
from collections import namedtuple, defaultdict
from csv import writer as csv_writer
from fractions import Fraction
from pathlib import Path


Score = namedtuple('Score', 'letter, gpa, percent, fraction')
Conversion = namedtuple('Conversion', 'letter, gpa, minimum, representative')


def mixed(whole, numer=0, denom=1, percent=False):
    result = Fraction(whole * denom + numer, denom)
    if percent:
        return result / 100
    else:
        return result


LETTERS = ['F', 'D', 'D+', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A']
GPAS = [0, *(float(Fraction(numer, 3)) for numer in range(3, 3 * 4 + 1))]
DEFAULT_BOUNDS = [
    mixed(00, 0, 1, percent=True),
    mixed(60, 0, 1, percent=True),
    mixed(65, 0, 1, percent=True),
    mixed(70, 0, 3, percent=True),
    mixed(73, 1, 3, percent=True),
    mixed(76, 2, 3, percent=True),
    mixed(80, 0, 3, percent=True),
    mixed(83, 1, 3, percent=True),
    mixed(86, 2, 3, percent=True),
    mixed(90, 0, 1, percent=True),
    mixed(95, 0, 1, percent=True),
]


def create_conversions(boundaries=None):
    if boundaries is None:
        boundaries = DEFAULT_BOUNDS
    boundaries = tuple(boundaries)
    if len(boundaries) != 11:
        raise ValueError(f'expected 11 lower boundaries, but got {len(boundaries)}')
    if boundaries[0] != 0:
        raise ValueError(f'lower boundary of first grade is not 0: {boundaries[0]}')
    if all(0 <= boundary <= 1 for boundary in boundaries):
        scale = Fraction(1)
    else:
        scale = Fraction(1, 100)
    boundaries = [
        scale * (boundary if isinstance(boundary, Fraction) else Fraction(boundary))
        for boundary in boundaries
    ]
    reps = [
        Fraction(0),
        *(
            (lower + upper) / 2 for lower, upper
            in zip(boundaries[1:], (*boundaries[2:], 1))
        ),
    ]
    return [Conversion(*parts) for parts in zip(LETTERS, GPAS, boundaries, reps)]


def from_letter(orig_letters, boundaries=None):
    conversion = create_conversions(boundaries)
    fractions = []
    for orig_letter in orig_letters.split('/'):
        if orig_letter == '':
            orig_letter = 'F'
        found = False
        for letter, _, _, frac in conversion:
            if orig_letter == letter:
                fractions.append(frac)
                found = True
                break
        if not found:
            raise ValueError(f'invalid letter grade "{orig_letter}"')
    mean_frac = mean(fractions)
    return from_fraction(mean_frac.numerator, mean_frac.denominator)


def from_fraction(numerator, denominator, boundaries=None):
    conversion = create_conversions(boundaries)
    if numerator < 0 or denominator < 0:
        raise ValueError(' '.join([
            'both numerator and denominator must be positive',
            f'but got {numerator} and {denominator}',
        ]))
    frac = Fraction(numerator, denominator)
    if not 0 <= frac <= 1:
        raise ValueError(f'invalid fraction "{frac}"')
    for letter, gpa, minimum, _ in reversed(conversion):
        if frac >= minimum:
            return Score(letter, gpa, float(frac), frac)
    letter = conversion[0].letter
    gpa = conversion[0].gpa
    return Score(letter, gpa, float(frac), frac)


def from_percent(percent, boundaries=None):
    conversion = create_conversions(boundaries)
    if not 0 <= percent <= 1:
        raise ValueError(f'invalid percentage "{repr(percent)}"')
    for letter, gpa, minimum, _ in reversed(conversion):
        if percent >= minimum:
            return Score(letter, gpa, percent, Fraction('{:.5f}'.format(percent)))
    letter = conversion[0].letter
    gpa = conversion[0].gpa
    return Score(letter, gpa, percent, Fraction('{:.5f}'.format(percent)))


def from_gpa(orig_gpa, boundaries=None):
    conversion = create_conversions(boundaries)
    if not 0 <= orig_gpa <= 4:
        raise ValueError(f'invalid GPA "{orig_gpa}"')
    prev_gpa = conversion[0].gpa
    for letter, gpa, _, frac in conversion:
        if prev_gpa <= orig_gpa < gpa:
            return Score(letter, orig_gpa, float(frac), frac)
    letter = conversion[-1].letter
    frac = conversion[-1].frac
    return Score(letter, orig_gpa, float(frac), frac)


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


Student = namedtuple('Student', 'first_name, last_name, email')


def student_from_str(line):
    regex = r'(?P<last_name>[^,]*), (?P<first_name>.*) <(?P<email>.*)>'
    return Student(**re.fullmatch(regex, line).groupdict())


class GradeBook:

    def __init__(self, filepath):
        with filepath.open() as fd:
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

    def to_csv(self, filepath):
        with filepath.open('w') as fd:
            fd.write('\t'.join([
                'Student',
                *(assignment.heading for assignment in self.assignments.traversal()),
            ]))
            fd.write('\n')
            for student in self.grades:
                fd.write('\t'.join([
                    f'{student.last_name}, {student.first_name} <{student.email}>',
                    *(
                        self.grades[student][assignment.qualified_name].score
                        for assignment in self.assignments.traversal()
                    ),
                ]))
                fd.write('\n')
