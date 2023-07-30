import csv
import io

from decimal import Decimal
from typing import cast, List, Optional, Sequence, Union

from . import central_line as cl
from .constants import ROUNDING
from .types import (
    TYPE_COUNTS_INPUT,
    TYPE_MOVING_RANGE_VALUE,
    TYPE_MOVING_RANGES,
)


CENTRAL_LINE_AVERAGE = 'average'


class Base:
    def __init__(
            self,
            counts: TYPE_COUNTS_INPUT,
            central_line: str = CENTRAL_LINE_AVERAGE,
            subset_start_index: int = 0,
            subset_end_index: Optional[int] = None,
    ):
        """

        :param counts: list of data to be used by the X chart
        :param subset_start_index: Optional starting index of counts to calculate limits from
        :param subset_end_index: Optional ending index of counts to calculate limits to
        """
        self.counts = [Decimal(str(x)) for x in counts]
        self._mr: TYPE_MOVING_RANGES = []
        self.i = max(0, subset_start_index)
        self.j = len(counts)
        if subset_end_index:
            self.j = min(self.j, subset_end_index)

        assert self.i <= self.j

        if central_line == CENTRAL_LINE_AVERAGE:
            self._cl = cl.Average(self.counts, self.i, self.j)

    def __repr__(self) -> str:
        result = ''
        for k, v in self.to_dict().items():
            k_format = '{0: <9}'.format(k)
            if isinstance(v, list):
                values = '[' + ', '.join(map(str, v)) + ']'
            else:
                values = v
            result += f'{k_format}: {values}\n'
        return result

    def x_to_dict(self) -> dict:
        """
        Return the values needed for the X chart as a dictionary
        """
        return {
            'values': self.counts,
            'unpl': self.upper_natural_process_limit(),
            'cl': self.x_central_line(),
            'lnpl': self.lower_natural_process_limit(),
        }

    def mr_to_dict(self) -> dict:
        """
        Return the values needed for the MR chart as a dictionary
        """
        return {
            'values': self.moving_ranges(),
            'url': self.upper_range_limit(),
            'cl': self.mr_central_line(),
        }

    def to_dict(self) -> dict:
        # Naming comes from pg. 163
        #   So Which Way Should You Compute Limits? from Making Sense of Data
        result = {}
        for k, v in self.x_to_dict().items():
            result[f'x_{k}'] = v
        for k, v in self.mr_to_dict().items():
            result[f'mr_{k}'] = v

        return result

    def to_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['x_values', 'x_unpl', 'x_cl', 'x_lnpl', 'mr_values', 'mr_url', 'mr_cl'])
        writer.writerows(zip(
            self.counts,
            self.upper_natural_process_limit(),
            self.x_central_line(),
            self.lower_natural_process_limit(),
            self.moving_ranges(),
            self.upper_range_limit(),
            self.mr_central_line()
        ))
        return output.getvalue()

    def moving_ranges(self) -> TYPE_MOVING_RANGES:
        """
        Moving ranges are the absolute differences between successive count values.
        The first element will always be None
        """
        if self._mr:
            return self._mr

        result: list[TYPE_MOVING_RANGE_VALUE] = []
        for i, c in enumerate(self.counts):
            if i == 0:
                result.append(None)
            else:
                value = cast(Union[Decimal, int], abs(c - self.counts[i - 1]))
                result.append(value)
        self._mr = result
        return self._mr

    def x_central_line(self) -> Sequence[Decimal]:
        return self._cl.x()

    def mr_central_line(self) -> Sequence[Decimal]:
        return self._cl.mr(self.moving_ranges())

    def upper_range_limit(self) -> Sequence[Decimal]:
        mr_cl = self.mr_central_line()
        limit = Decimal('3.268') * mr_cl[0]
        value = round(limit, ROUNDING)
        return [value] * len(mr_cl)

    def upper_natural_process_limit(self) -> Sequence[Decimal]:
        limit = self.x_central_line()[0] + (Decimal('2.660') * self.mr_central_line()[0])
        value = round(limit, ROUNDING)
        return [value] * len(self.counts)

    def lower_natural_process_limit(self) -> Sequence[Decimal]:
        """
        LNPL can be negative.
        It's the caller's responsibility to take max(LNPL, 0) if a negative LNPL does not make sense
        """
        limit = self.x_central_line()[0] - (Decimal('2.660') * self.mr_central_line()[0])
        value = round(limit, ROUNDING)
        return [value] * len(self.counts)

    def rule_1_x_indices_beyond_limits(
            self,
            upper_limit: Optional[Decimal] = None,
            lower_limit: Optional[Decimal] = None,
    ) -> List[bool]:
        """
        Points Outside the Limits

        A single point outside the computed limits
        on either the X Chart, or the mR Chart,
        should be interpreted as an indication of
        the presence of an assignable cause which has a *dominant* effect.

        :param upper_limit: Optional - Will default to the Upper Natural Process Limit
        :param lower_limit: Optional - Will default to the Lower Natural Process Limit

        :return: list[bool] A list of boolean values of length(counts)
            True at index i means that self.counts[i] is above the upper_limit or below the lower_limit
        """
        n = len(self.counts)
        upper = self.upper_natural_process_limit()
        if upper_limit:
            upper = [upper_limit] * n

        lower = self.lower_natural_process_limit()
        if lower_limit:
            lower = [lower_limit] * n

        return self._points_beyond_limits(self.counts, upper, lower)

    def rule_1_mr_indices_beyond_limits(self) -> List[bool]:
        """
        Points Outside the Limits

        A single point outside the computed limits
        on either the X Chart, or the mR Chart,
        should be interpreted as an indication of
        the presence of an assignable cause which has a *dominant* effect.

        :return: list[bool] A list of boolean values of length(self.moving_ranges())
            True at index i means that self.moving_ranges()[i] is above the Upper Range Limit
        """
        return self._points_beyond_limits(self.moving_ranges(), self.upper_range_limit())

    def rule_2_runs_about_central_line(self) -> List[bool]:
        """
        Runs About the Central Line

        Eight successive values,
        all on the same side of the central line on the X Chart
        may be interpreted as an indication of
        the presence of an assignable cause which has a *weak* but sustained effect.

        :return: list[bool] A list of boolean values of length(counts)
            True at index i means that self.counts[i] is above the line and part of a run of eight successive values
        """

        result = [False] * len(self.counts)

        # positive is number of consecutive points above the line
        # negative is number of consecutive points below the line
        run = 0
        for i, (x, cl) in enumerate(zip(self.counts, self.x_central_line())):
            if x > cl:
                if run < 0:
                    run = 1
                else:
                    run += 1
            elif x < cl:
                if run > 0:
                    run = -1
                else:
                    run -= 1

            if abs(run) == 8:
                for j in range(8):
                    result[i - j] = True
            elif abs(run) > 8:
                result[i] = True

        return result

    def rule_3_runs_near_limits(self) -> List[bool]:
        """
        Runs Near the Limits

        Three out of four successive values on the X Chart
        all within the upper 25% of the region between the limits, or
        all within the lower 25% of the region between the limits,
        may be interpreted as an indication of the presence
        of an assignable cause which has a *moderate* but sustained effect.
        """
        result = [False] * len(self.counts)

        # positive value is point near upper limit
        # negative value is point near lower limit
        near_limits = [0] * len(self.counts)

        values = zip(self.counts, self.upper_natural_process_limit(), self.lower_natural_process_limit())
        for i, (x, unpl, lnpl) in enumerate(values):
            upper_25 = ((unpl - lnpl) * Decimal('.75')) + lnpl
            lower_25 = ((unpl - lnpl) * Decimal('.25')) + lnpl
            if x < lower_25:
                near_limits[i] = -1

            if x > upper_25:
                near_limits[i] = 1

            if i >= 3:
                successive_values = near_limits[i - 3:i + 1]
                if abs(sum(successive_values)) >= 3:
                    for j in range(i - 3, i + 1):
                        result[j] = True

        return result

    @staticmethod
    def _points_beyond_limits(
            data: TYPE_MOVING_RANGES,
            upper_limits: Sequence[Decimal],
            lower_limits: Optional[Sequence[Decimal]] = None
    ) -> List[bool]:
        result = [False] * len(data)

        if lower_limits is None:
            lower_limits = [Decimal('-Inf')] * len(upper_limits)

        for i, (x, w, y) in enumerate(zip(data, lower_limits, upper_limits)):
            if x is None:  # first index of Moving Ranges
                continue

            if not w <= x <= y:
                result[i] = True

        return result
