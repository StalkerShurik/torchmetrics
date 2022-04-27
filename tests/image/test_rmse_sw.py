# Copyright The PyTorch Lightning team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import namedtuple
from functools import partial

import pytest
import sewar
import torch

from tests.helpers.testers import BATCH_SIZE, NUM_BATCHES, MetricTester
from torchmetrics import RootMeanSquaredErrorUsingSlidingWindow
from torchmetrics.functional import root_mean_squared_error_using_sliding_window

Input = namedtuple("Input", ["preds", "target", "window_size"])

_inputs = []
for size, channel, window_size, dtype in [
    (12, 3, 3, torch.float),
    (13, 1, 4, torch.float32),
    (14, 1, 5, torch.double),
    (15, 3, 8, torch.float64),
]:
    preds = torch.rand(NUM_BATCHES, BATCH_SIZE, channel, size, size, dtype=dtype)
    target = torch.rand(NUM_BATCHES, BATCH_SIZE, channel, size, size, dtype=dtype)
    _inputs.append(Input(preds=preds, target=target, window_size=window_size))


def _sewar_rmse_sw(preds, target, window_size):
    rmse_mean = torch.tensor(0.0, dtype=preds.dtype)

    preds = preds.permute(0, 2, 3, 1).numpy()
    target = target.permute(0, 2, 3, 1).numpy()

    for idx, (pred, tgt) in enumerate(zip(preds, target)):
        rmse, _ = sewar.rmse_sw(tgt, pred, window_size)
        rmse_mean += (rmse - rmse_mean) / (idx + 1)

    return rmse_mean


@pytest.mark.parametrize("preds, target, window_size", [(i.preds, i.target, i.window_size) for i in _inputs])
class TestRootMeanSquareErrorWithSlidingWindow(MetricTester):
    @pytest.mark.parametrize("ddp", [False])
    @pytest.mark.parametrize("dist_sync_on_step", [False, True])
    def test_rmse_sw(self, preds, target, window_size, ddp, dist_sync_on_step):
        self.run_class_metric_test(
            ddp,
            preds,
            target,
            RootMeanSquaredErrorUsingSlidingWindow,
            partial(_sewar_rmse_sw, window_size=window_size),
            metric_args={"window_size": window_size},
            dist_sync_on_step=dist_sync_on_step,
        )

    def test_rmse_sw_functional(self, preds, target, window_size):
        self.run_functional_metric_test(
            preds,
            target,
            root_mean_squared_error_using_sliding_window,
            partial(_sewar_rmse_sw, window_size=window_size),
            metric_args={"window_size": window_size},
        )