import h3


def test_coordinates_produce_valid_h3_cell_and_boundary() -> None:
    cell = h3.latlng_to_cell(27.264, 92.425, 7)

    assert h3.is_valid_cell(cell)
    assert len(h3.cell_to_boundary(cell)) == 6
