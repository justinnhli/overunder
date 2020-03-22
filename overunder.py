"""A gradebook library."""

import re
from fractions import Fraction
from pathlib import Path


class NamedNode:
    """A tree where nodes are named hierarchically."""

    def __init__(self, name):
        # type: (str) -> None
        """Initialize the NamedNode."""
        self.name = name
        self._parent = None # type: Optional[NamedNode]
        self._depth = 0
        self._children = [] # type: List[NamedNode]

    def __contains__(self, qualified_name):
        # type: (str) -> bool
        try:
            self.get(qualified_name)
            return True
        except KeyError:
            return False

    def __getitem__(self, qualified_name):
        # type: (str) -> NamedNode
        return self.get(qualified_name)

    @property
    def qualified_name(self):
        # type: () -> str
        """Get the qualified name of the NamedNode."""
        names = [self.name]
        curr = self
        while curr.parent is not None:
            curr = curr.parent
            names.append(curr.name)
        return '__'.join(reversed(names))

    @property
    def parent(self):
        # type: () -> Optional[NamedNode]
        """Get the parent of the NamedNode."""
        return self._parent

    @property
    def ancestors(self):
        # type: () -> Generator[NamedNode, None, None]
        """Yield the ancestors of the NamedNode."""
        curr = self
        while curr.parent:
            curr = curr.parent
            yield curr

    @property
    def index(self):
        # type: () -> int
        """Get the index of the NamedNode."""
        return self._parent.index_of(self.name)

    @property
    def depth(self):
        # type: () -> int
        """Get the depth of the NamedNode."""
        return self._depth

    @property
    def num_children(self):
        # type: () -> int
        """Get the number of children of the NamedNode."""
        return len(self._children)

    @property
    def children(self):
        # type: () -> Generator[NamedNode, None, None]
        """Yield the children of the NamedNode."""
        yield from self._children

    @property
    def is_leaf(self):
        # type: () -> bool
        """Return whether the NamedNode is a leaf."""
        return not self._children

    @property
    def traversal(self):
        # type: () -> Generator[NamedNode, None, None]
        """Yield all descendant NamedNodes."""
        yield self
        for child in self._children:
            yield from child.traversal

    def index_of(self, name):
        # type: (str) -> int
        """Get the index of the child with the given name."""
        for i, child in enumerate(self._children):
            if child.name == name:
                return i
        raise KeyError(name)

    def get(self, qualified_name):
        # type: (str) -> NamedNode
        """Get the NamedNode."""
        names = qualified_name.split('__')
        assert names[0] == self.name, f'"{names[0]}" != "{self.name}"'
        return self._get(names)

    def _get(self, names):
        # type: (List[str]) -> NamedNode
        if len(names) == 1:
            return self
        else:
            index = self.index_of(names[1])
            return self._children[index]._get(names[1:]) # pylint: disable = protected-access

    def propagate(self):
        # type: () -> None
        """Propagate information to ancestors."""
        pass

    def add_child(self, node):
        # type: (NamedNode) -> None
        # pylint: disable = protected-access
        """Add a child to this NamedNode."""
        self._children.append(node)
        node._parent = self
        node._depth = self._depth + 1
        node.propagate()

    def add_descendant(self, qualified_name, node):
        # type: (str, NamedNode) -> None
        """Add a descendant to this NamedNode."""
        names = qualified_name.split('__')
        assert names[0] == self.name
        assert len(names) > 1
        self._add_descendant(names, node)

    def _add_descendant(self, names, node):
        # type: (List[str], NamedNode) -> None
        if len(names) == 2:
            self.add_child(node)
        else:
            index = self.index_of(names[1])
            # pylint: disable = protected-access
            self._children[index]._add_descendant(names[1:], node)

    def move_node(self, old_qualified_name, new_qualified_name):
        # type: (str, str) -> None
        """Move the specified node to a new location."""
        self.add_descendant(new_qualified_name, self.remove_node(old_qualified_name))

    def move_node_up(self, qualified_name):
        # type: (str) -> None
        """Swap the node with its nearest elder sibling."""
        names = qualified_name.split('__')
        assert names[0] == self.name
        assert len(names) > 1
        descendant = self._get(names)
        children = descendant.parent._children
        index = descendant.parent.index_of(names[-1])
        if index > 0:
            children[index - 1], children[index] = children[index], children[index - 1]

    def move_node_down(self, qualified_name):
        # type: (str) -> None
        """Swap the node with its closest younger sibling."""
        names = qualified_name.split('__')
        assert names[0] == self.name
        assert len(names) > 1
        descendant = self._get(names)
        children = descendant.parent._children
        index = descendant.parent.index_of(names[-1])
        if index < len(children) - 1:
            children[index], children[index + 1] = children[index + 1], children[index]

    def remove_node(self, qualified_name):
        # type: (str) -> NamedNode
        """Remove the node."""
        names = qualified_name.split('__')
        assert names[0] == self.name
        assert len(names) > 1
        descendant = self._get(names)
        index = descendant.parent.index_of(names[-1])
        return descendant.parent._children.pop(index) # pylint: disable = protected-access

    def to_heading(self):
        # type: () -> str
        """Get the underscore-prefixed heading for this NamedNode."""
        return f'{self.depth * "__"}{self}'

    def pretty_print(self, depth=0):
        # type: (int) -> None
        """Print the NamedNode and its descendants, with indentation."""
        print(self.to_heading())
        for child in self.children:
            child.pretty_print(depth + 1)


class Assignment(NamedNode):
    """An assignment with a specific weight."""

    def __init__(self, name, weight_str, extra_credit=False):
        # type: (str, str, bool) -> None
        """Initialize the Assignment."""
        super().__init__(name)
        self._weight_str = weight_str
        self.extra_credit = extra_credit
        self._weight = self._parse_weight_str(self._weight_str)

    def _parse_weight_str(self, weight_str):
        # type: (str) -> Fraction
        # pylint: disable = no-self-use
        if weight_str.endswith('%'):
            return Fraction(weight_str[:-1]) / Fraction(100)
        elif '/' in weight_str:
            numerator, denominator = weight_str.split('/')
            return Fraction(numerator) / Fraction(denominator)
        elif re.fullmatch('[0-9.]*', weight_str):
            return Fraction(weight_str)
        else:
            raise ValueError(f'invalid weight string: {weight_str}')

    def __str__(self):
        # type: () -> str
        return f'{self.name}{"*" if self.extra_credit else ""} ({self._weight_str})'

    @property
    def percent_weight(self):
        # type: () -> Fraction
        """Get the weight as a percentage of its siblings' total."""
        if self.parent is None:
            return Fraction(1)
        elif self._weight_str.endswith('%') or '/' in self._weight_str:
            return self._weight
        elif re.fullmatch('[0-9.]*', self._weight_str):
            return self._weight / sum(child._weight for child in self.parent.children)
        else:
            raise ValueError(f'invalid weight string: {self._weight_str}')


class AssignmentGrade(NamedNode):
    """A grade for a specific assignment."""

    def __init__(self, assignment, grade_str):
        # type: (Assignment, str) -> None
        """Initialize this AssignmentGrade."""
        super().__init__(assignment.name)
        self.assignment = assignment
        self._grade_str = grade_str
        self.percent_grade = self._parse_grade_str()

    def _parse_grade_str(self):
        # type: () -> Optional[Fraction]
        if self._grade_str.lower() == 'none':
            return None
        grade_str = self._grade_str
        negative = grade_str.startswith('-')
        if negative:
            grade_str = grade_str[1:]
        if grade_str.endswith('%'):
            percent_grade = Fraction(grade_str[:-1]) / Fraction(100)
        elif '/' in grade_str:
            numerator, denominator = grade_str.split('/')
            if numerator == '':
                numerator = '0'
            if denominator == '':
                denominator = '1'
            percent_grade = Fraction(numerator) / Fraction(denominator)
        elif re.fullmatch('[0-9.]*', grade_str):
            percent_grade = Fraction(grade_str) / self.assignment.weight
        else:
            assert False
        if negative:
            return 1 - percent_grade
        else:
            return percent_grade

    def __str__(self):
        # type: () -> str
        return f'{self.assignment}: {self.export_str}'

    @property
    def extra_credit(self):
        # type: () -> bool
        """Return whether this assignment is extra credit."""
        return self.assignment.extra_credit

    @property
    def percent_weight(self):
        # type: () -> Fraction
        """Get the weight as a percentage of its siblings' total."""
        return self.assignment.percent_weight

    @property
    def display_str(self):
        # type: () -> str
        """Get a human-readable grade."""
        if self.is_leaf:
            return self._grade_str
        else:
            return f'{float(self.percent_grade):.2%}'

    @property
    def export_str(self):
        # type: () -> str
        """Return this grade as a string for export."""
        if self.is_leaf:
            return self._grade_str
        else:
            return f'{float(self.minimum_grade):.2%}'

    def propagate(self):
        # type: () -> None
        """Propagate information to ancestors."""
        if not self.is_leaf:
            self.percent_grade = sum(
                child.percent_grade * child.assignment.percent_weight
                for child in self.children
            )
        if self.parent is not None:
            self.parent.propagate()

    def set_grade(self, grade_str):
        # type: (str) -> None
        """Set a new grade."""
        self._grade_str = grade_str
        self.percent_grade = self._parse_grade_str()
        self.propagate()


class Student:
    """A student."""

    def __init__(self, first_name, last_name, email):
        # type: (str, str, str) -> None
        """Initialize a Student."""
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self._alias = None # type: Optional[str]

    @property
    def alias(self):
        # type: () -> str
        """Get the email alias."""
        if self._alias is None:
            self._alias = self.email.split('@')[0]
        return self._alias


class GradeBook:
    """A collection of assignment grades for students."""

    def __init__(self, csv_path):
        # type: (Path) -> None
        """Initialize the GradeBook."""
        self.csv_path = csv_path.expanduser().resolve()
        self.assignments = None # type: Optional[Assignment]
        self.students = {} # type: Dict[str, Student]
        self.grades = {} # type: Dict[str, AssignmentGrade]
        self._read_csv()

    def _read_csv(self):
        # type: () -> None
        with self.csv_path.open() as fd:
            headings = re.sub('  +', '\t', fd.readline().strip())
            self.assignments = self._create_assignments(headings.split('\t')[1:])
            for line in fd.readlines():
                line = re.sub('  +', '\t', line.strip())
                student_str, *grade_strs = line.split('\t')
                student = self._create_student(student_str)
                self.students[student.alias] = student
                self.grades[student.alias] = self._create_grades(self.assignments, grade_strs)

    def _create_assignments(self, headings):
        # type: (List[str]) -> Assignment
        # pylint: disable = no-self-use
        heading_regex = r'(?P<indent>(__)*)(?P<name>[^*]*)(?P<extra_credit>\*?) \((?P<weight_str>[^)]*)\)'
        stack = [] # type: List[Assignment]
        for heading in headings:
            match = re.fullmatch(heading_regex, heading)
            assert match is not None
            depth = len(match.group('indent')) // 2
            name = match.group('name')
            extra_credit = bool(match.group('extra_credit'))
            weight_str = match.group('weight_str')
            stack = stack[:depth]
            assignment = Assignment(name, weight_str, extra_credit=extra_credit)
            if len(stack) > 0:
                stack[-1].add_child(assignment)
            stack.append(assignment)
        return stack[0]

    def _create_student(self, student_str):
        # type: (str) -> Student
        # pylint: disable = no-self-use
        student_regex = r'(?P<last_name>[^,]*), (?P<first_name>.*) <(?P<email>[^>]*)>'
        match = re.fullmatch(student_regex, student_str)
        return Student(match.group('first_name'), match.group('last_name'), match.group('email'))

    def _create_grades(self, assignments, grade_strs):
        # type: (Assignment, List[str]) -> AssignmentGrade
        # pylint: disable = no-self-use
        stack = [] # type: List[AssignmentGrade]
        for assignment, grade_str in zip(assignments.traversal, grade_strs):
            stack = stack[:assignment.depth]
            assignment_grade = AssignmentGrade(assignment, grade_str)
            if len(stack) > 0:
                stack[-1].add_child(assignment_grade)
            stack.append(assignment_grade)
        return stack[0]

    def add_assignment(self, qualified_name, weight_str):
        # type: (str, str) -> None
        """Add an assignment to the GradeBook."""
        assignment = Assignment(qualified_name.split('__')[-1], weight_str)
        self.assignments.add_descendant(qualified_name, assignment)
        for assignment_grade_root in self.grades.values():
            assignment_grade_root.add_descendant(
                qualified_name,
                AssignmentGrade(assignment, '0%'), # FIXME initial grade
            )

    def move_assignment_up(self, qualified_name):
        # type: (str) -> None
        """Swap the assignment with its closest elder sibling."""
        self.assignments.move_node_up(qualified_name)
        for assignment_grade_root in self.grades.values():
            assignment_grade_root.move_node_up(qualified_name)

    def move_assignment_down(self, qualified_name):
        # type: (str) -> None
        """Swap the assignment with its closest younger sibling."""
        self.assignments.move_node_down(qualified_name)
        for assignment_grade_root in self.grades.values():
            assignment_grade_root.move_node_down(qualified_name)

    def remove_assignment(self, qualified_name):
        # type: (str) -> None
        """Remove the assignment."""
        self.assignments.remove_node(qualified_name)
        for assignment_grade_root in self.grades.values():
            assignment_grade_root.remove_node(qualified_name)

    def get_grade(self, alias, qualified_name):
        # type: (str, str) -> AssignmentGrade
        """Get the grade for the student and assignment."""
        return self.grades[alias][qualified_name]

    def set_grade(self, alias, qualified_name, grade_str):
        # type: (str, str, str) -> None
        """Set the grade for the student and assignment."""
        self.grades[alias][qualified_name].set_grade(grade_str)

    def write_csv(self):
        # type: () -> None
        """Export the GradeBook to a csv file."""
        with self.csv_path.parent.joinpath(self.csv_path.name + '-new').open('w') as fd:
            fd.write('\t'.join([
                'Student',
                *(assignment.to_heading() for assignment in self.assignments.traversal),
            ]))
            fd.write('\n')
            for alias, assignment_grade_root in self.grades.items():
                student = self.students[alias]
                fd.write('\t'.join([
                    f'{student.last_name}, {student.first_name} <{student.email}>',
                    *(assignment_grade.export_str for assignment_grade in assignment_grade_root.traversal)
                ]))
                fd.write('\n')


def test():
    # type: () -> None
    """Test OverUnder."""
    gradebook = GradeBook(Path('grades.csv'))
    gradebook.add_assignment('DataStructures__Homeworks__HW1__Q1a', '10')
    tuple(gradebook.grades.values())[0].pretty_print()
    print()
    gradebook.move_assignment_up('DataStructures__Homeworks__HW5')
    gradebook.move_assignment_down('DataStructures__Homeworks__HW4')
    gradebook.move_assignment_up('DataStructures__Homeworks__HW4')
    tuple(gradebook.grades.values())[0].pretty_print()
    print()
    gradebook.remove_assignment('DataStructures__Homeworks__HW1__Q1a')
    tuple(gradebook.grades.values())[0].pretty_print()
    print()
    gradebook.write_csv()


def main():
    # type: () -> None
    """Initialize a GradeBook csv file."""
    raise NotImplementedError() # FIXME


if __name__ == '__main__':
    main()
