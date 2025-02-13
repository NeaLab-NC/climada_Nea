"""
This file is part of CLIMADA.

Copyright (C) 2017 ETH Zurich, CLIMADA contributors listed in AUTHORS.

CLIMADA is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free
Software Foundation, version 3.

CLIMADA is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with CLIMADA. If not, see <https://www.gnu.org/licenses/>.

---

Define ImpactFunc class.
"""

__all__ = ['ImpactFunc']

import logging
import numpy as np
import matplotlib.pyplot as plt

import climada.util.checker as u_check

LOGGER = logging.getLogger(__name__)

class ImpactFunc():
    """Contains the definition of one impact function.

    Attributes
    ----------
    haz_type : str
        hazard type acronym (e.g. 'TC')
    id : int or str
        id of the impact function. Exposures of the same type
        will refer to the same impact function id
    name : str
        name of the ImpactFunc
    intensity_unit : str
        unit of the intensity
    intensity : np.array
        intensity values
    mdd : np.array
        mean damage (impact) degree for each intensity (numbers
        in [0,1])
    paa : np.array
        percentage of affected assets (exposures) for each
        intensity (numbers in [0,1])
    """
    def __init__(self):
        """Empty initialization."""
        self.id = ''
        self.name = ''
        self.intensity_unit = ''
        self.haz_type = ''
        # Followng values defined for each intensity value
        self.intensity = np.array([])
        self.mdd = np.array([])
        self.paa = np.array([])

    def calc_mdr(self, inten):
        """Interpolate impact function to a given intensity.

        Parameters
        ----------
        inten : float or np.array
            intensity, the x-coordinate of the
            interpolated values.

        Returns
        -------
        np.array
        """
#        return np.interp(inten, self.intensity, self.mdd * self.paa)
        return np.interp(inten, self.intensity, self.paa) * \
            np.interp(inten, self.intensity, self.mdd)

    def plot(self, axis=None, **kwargs):
        """Plot the impact functions MDD, MDR and PAA in one graph, where
        MDR = PAA * MDD.

        Parameters
        ----------
        axis : matplotlib.axes._subplots.AxesSubplot, optional
            axis to use
        kwargs : optional
            arguments for plot matplotlib function, e.g. marker='x'

        Returns
        -------
        matplotlib.axes._subplots.AxesSubplot
        """
        if axis is None:
            _, axis = plt.subplots(1, 1)

        title = '%s %s' % (self.haz_type, str(self.id))
        if self.name != str(self.id):
            title += ': %s' % self.name
        axis.set_xlabel('Intensity (' + self.intensity_unit + ')')
        axis.set_ylabel('Impact (%)')
        axis.set_title(title)
        axis.plot(self.intensity, self.mdd * 100, 'b', label='MDD', **kwargs)
        axis.plot(self.intensity, self.paa * 100, 'r', label='PAA', **kwargs)
        axis.plot(self.intensity, self.mdd * self.paa * 100, 'k--', label='MDR', **kwargs)

        axis.set_xlim((self.intensity.min(), self.intensity.max()))
        axis.legend()
        return axis

    def check(self):
        """Check consistent instance data.

        Raises
        ------
        ValueError
        """
        num_exp = len(self.intensity)
        u_check.size(num_exp, self.mdd, 'ImpactFunc.mdd')
        u_check.size(num_exp, self.paa, 'ImpactFunc.paa')

        if num_exp == 0:
            LOGGER.warning("%s impact function with name '%s' (id=%s) has empty"
                           " intensity.", self.haz_type, self.name, self.id)
            return

        # Warning for non-vanishing impact at intensity 0. If positive
        # and negative intensity warning for interpolation at intensity 0.
        zero_idx = np.where(self.intensity == 0)[0]
        if zero_idx.size != 0:
            if self.mdd[zero_idx[0]] != 0 or self.paa[zero_idx[0]] != 0:
                LOGGER.warning('For intensity = 0, mdd != 0 or paa != 0. '
                               'Consider shifting the origin of the intensity '
                               'scale. In impact.calc the impact is always '
                               'null at intensity = 0.')
        elif self.intensity[0] < 0 < self.intensity[-1]:
            LOGGER.warning('Impact function might be interpolated to non-zero'
                           ' value at intensity = 0. Consider shifting the '
                           'origin of the intensity scale. In impact.calc '
                           'the impact is always null at intensity = 0.')

    @classmethod
    def from_step_impf(cls, intensity, mdd=(0, 1), paa=(1, 1), impf_id=1):

        """ Step function type impact function.

        By default, everything is destroyed above the step.
        Useful for high resolution modelling.

        This method modifies self (climada.entity.impact_funcs instance)
        by assigning an id, intensity, mdd and paa to the impact function.

        Parameters
        ----------
        intensity: tuple(float, float, float)
            tuple of 3-intensity numbers: (minimum, threshold, maximum)
        mdd: tuple(float, float)
            (min, max) mdd values. The default is (0, 1)
        paa: tuple(float, float)
            (min, max) paa values. The default is (1, 1)
        impf_id : int, optional, default=1
            impact function id

        Return
        ------
        impf : climada.entity.impact_funcs.ImpactFunc
            Step impact function

        """

        impf = cls()
        impf.id = impf_id
        inten_min, threshold, inten_max = intensity
        impf.intensity = np.array([inten_min, threshold, threshold, inten_max])
        paa_min, paa_max = paa
        impf.paa = np.array([paa_min, paa_min, paa_max, paa_max])
        mdd_min, mdd_max = mdd
        impf.mdd = np.array([mdd_min, mdd_min, mdd_max, mdd_max])

        return impf

    def set_step_impf(self, *args, **kwargs):
        """This function is deprecated, use ImpactFunc.from_step_impf instead."""
        LOGGER.warning("The use of ImpactFunc.set_step_impf is deprecated."
                        " Use ImpactFunc.from_step_impf instead.")
        self.__dict__ = ImpactFunc.from_step_impf(*args, **kwargs).__dict__

    @classmethod
    def from_sigmoid_impf(cls, intensity, L, k, x0, if_id=1):
        """ Sigmoid type impact function hinging on three parameter.

        This type of impact function is very flexible for any sort of study,
        hazard and resolution. The sigmoid is defined as:

        .. math::
            f(x) = \frac{L}{1+exp^{-k(x-x0)}}

        For more information: https://en.wikipedia.org/wiki/Logistic_function

        This method modifies self (climada.entity.impact_funcs instance)
        by assining an id, intensity, mdd and paa to the impact function.

        Parameters
        ----------
            intensity: tuple(float, float, float)
                tuple of 3 intensity numbers along np.arange(min, max, step)
            L : float
                "top" of sigmoid
            k : float
                "slope" of sigmoid
            x0 : float
                intensity value where f(x)==L/2
            if_id : int, optional, default=1
                impact function id

        Return
        ------
        impf : climada.entity.impact_funcs.ImpactFunc
            Step impact function

        """
        impf = cls()
        impf.id = if_id
        inten_min, inten_max, inten_step = intensity
        impf.intensity = np.arange(inten_min, inten_max, inten_step)
        impf.paa = np.ones(len(impf.intensity))
        impf.mdd = L / (1 + np.exp(-k * (impf.intensity - x0)))

        return impf

    def set_sigmoid_impf(self, *args, **kwargs):
        """This function is deprecated, use LitPop.from_countries instead."""
        LOGGER.warning("The use of ImpactFunc.set_sigmoid_impf is deprecated."
                       "Use ImpactFunc.from_sigmoid_impf instead.")
        self.__dict__ = ImpactFunc.from_sigmoid_impf(*args, **kwargs).__dict__


