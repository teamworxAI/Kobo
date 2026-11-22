import pandas as pd

from wema import charts


def test_dot_ci_pads_percentage_axis_boundaries():
    groups = ["All", "Secondary or less", "College / university", "Postgraduate", "Other"]
    data = pd.DataFrame([
        {"Indicator": "Aware", "Group": group, "p": 0.5, "lo": 0.4, "hi": 0.6,
         "n": 100, "k": 50, "small": False}
        for group in groups
    ])

    fig = charts.dot_ci(data, group_order=groups)

    assert fig.layout.xaxis.range == (-0.05, 1.15)
    assert fig.layout.xaxis.tick0 == 0
