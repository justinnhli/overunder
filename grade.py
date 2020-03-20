from collections import namedtuple
from fractions import Fraction

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

