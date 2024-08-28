from typing import List

import numpy as np


def generate_color_gradient(data_names) -> List[str]:
    """
    Generate a gradient of colors from red to green to blue for a list of data names.

    Args:
        - **data_names**: `list[str]`: Arbitrary list of data names. A hex color code will be generated for each data name.

    Returns:
        List of hex color codes for each name in data_names.

    """
    num_data = len(data_names)

    red_to_green = np.linspace([1, 0, 0], [0, 1, 0], num=int(np.ceil(num_data / 2)), endpoint=False)
    green_to_blue = np.linspace([0, 1, 0], [0, 0, 1], num=int(np.ceil(num_data / 2 + 1)))

    full_gradient = np.vstack([red_to_green, green_to_blue])[1:num_data + 1]

    hex_colors = ['#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255)) for r, g, b in full_gradient]

    return hex_colors

