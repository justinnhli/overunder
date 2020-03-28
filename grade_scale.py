from fractions import Fraction

class GradeScale:

    LETTERS = ['F', 'D', 'D+', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A']

    def __init__(self, boundaries=None):
        if boundaries is None:
            boundaries = [
                Fraction(0, 300),
                Fraction(180, 300),
                Fraction(195, 300),
                Fraction(210, 300),
                Fraction(220, 300),
                Fraction(230, 300),
                Fraction(240, 300),
                Fraction(250, 300),
                Fraction(260, 300),
                Fraction(270, 300),
                Fraction(285, 300),
                Fraction(300, 300),
            ]
        self.boundaries = boundaries

    def from_letter(self, letter, fixme='maximum'):
        index = self.LETTERS.index(letter)
        if fixme == 'minimum':
            return self.boundaries[index]
        elif fixme == 'maximum':
            return self.boundaries[index + 1]
        else:
            return (self.boundaries[index] + self.boundaries[index + 1]) / 2

    def from_fraction(self, fraction):
        pass

    def from_percent(self, percent):
        pass

    def from_gpa(self, gpa):
        pass


class Grade:

    def __init__(self, scale, letter, gpa, fraction):
        self.scale = None
        self.letter = None
        self.gpa = None
        self.fraction = None

    def __add__(self, other):
        pass

    def __mul__(self, other):
        pass

    def __str__(self):
        pass
