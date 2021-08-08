# Copyright (C) 2021 Unitary Fund
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import copy
from typing import cast, FrozenSet, List, Set

import numpy as np
import cirq

from mitiq.observable.pauli import PauliString


class Observable:
    def __init__(self, *paulis: PauliString) -> None:
        self._paulis = set(paulis)
        self._nterms = len(self._paulis)

    @property
    def nterms(self) -> int:
        return self._nterms

    def _qubits(self) -> Set[cirq.Qid]:
        """Returns all qubits acted on by the Observable."""
        return {q for pauli in self._paulis for q in pauli._pauli.qubits}

    @property
    def qubit_indices(self) -> List[int]:
        return [cast(cirq.LineQubit, q).x for q in sorted(self._qubits())]

    @property
    def nqubits(self) -> int:
        return len(self.qubit_indices)

    def partition(self) -> Set[FrozenSet[PauliString]]:
        plists: List[List[PauliString]] = []
        paulis = copy.deepcopy(self._paulis)

        while paulis:
            pauli = paulis.pop()
            added = False
            for (i, plist) in enumerate(plists):
                if all(pauli.can_be_measured_with(p) for p in plist):
                    plists[i].append(pauli)
                    added = True
                    break

            if not added:
                plists.append([pauli])

        return set([frozenset(plist) for plist in plists])

    def _measure_in(self, circuit: cirq.Circuit) -> List[cirq.Circuit]:
        circuits: List[cirq.Circuit] = []
        base_circuit = copy.deepcopy(circuit)

        for pset in self.partition():
            basis_rotations = set()
            qubits_to_measure = set()
            for pauli in pset:
                basis_rotations.update(pauli._basis_rotations())
                qubits_to_measure.update(pauli._qubits_to_measure())
            circuits.append(
                base_circuit
                + basis_rotations
                + cirq.measure(*sorted(qubits_to_measure))
            )

        return circuits

    def matrix(self, dtype: type = np.complex128) -> np.ndarray:
        """Returns the (potentially very large) matrix of the Observable."""
        qubit_indices = self.qubit_indices
        n = self.nqubits

        matrix = np.zeros(shape=(2 ** n, 2 ** n), dtype=dtype)
        for pauli in self._paulis:
            matrix += pauli.matrix(
                qubit_indices_to_include=qubit_indices
            ).astype(dtype=dtype)

        return matrix