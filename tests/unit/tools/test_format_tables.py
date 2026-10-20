from tools.format_tables import display_width, format_text, main

UNALIGNED = "| a | bb |\n|---|---|\n| longer cell | x |\n"
ALIGNED = "| a           | bb  |\n| ----------- | --- |\n| longer cell | x   |\n"


def test_aligns_columns_to_the_widest_cell():
    assert format_text(UNALIGNED) == ALIGNED


def test_is_idempotent():
    assert format_text(ALIGNED) == ALIGNED


def test_text_around_the_table_is_untouched():
    assert format_text("Intro\n\n" + UNALIGNED + "\nOutro\n") == "Intro\n\n" + ALIGNED + "\nOutro\n"


def test_alignment_colons_are_kept():
    text = "| a | b | c |\n|:--|--:|:-:|\n| 1 | 2 | 3 |\n"
    assert format_text(text) == "| a   |   b |  c  |\n| :-- | --: | :-: |\n| 1   |   2 |  3  |\n"


def test_tables_in_code_fences_are_not_touched():
    fenced = "```\n" + UNALIGNED + "```\n"
    assert format_text(fenced) == fenced


def test_a_table_after_a_code_fence_is_formatted():
    assert format_text("```\ncode\n```\n" + UNALIGNED) == "```\ncode\n```\n" + ALIGNED


def test_wide_characters_count_as_two_cells():
    assert display_width("✅") == 2
    assert display_width("✓") == 1
    out = format_text("| a | b |\n|---|---|\n| ✅ | x |\n")
    assert out == "| a   | b   |\n| --- | --- |\n| ✅  | x   |\n"


def test_escaped_pipes_stay_inside_their_cell():
    out = format_text("| a | b |\n|---|---|\n| x \\| y | z |\n")
    assert out == "| a      | b   |\n| ------ | --- |\n| x \\| y | z   |\n"


def test_indented_tables_keep_their_indent():
    indented = "  | a | b |\n  |---|---|\n  | 1 | 2 |\n"
    assert format_text(indented) == "  | a   | b   |\n  | --- | --- |\n  | 1   | 2   |\n"


def test_crlf_line_endings_are_kept():
    assert format_text(UNALIGNED.replace("\n", "\r\n")) == ALIGNED.replace("\n", "\r\n")


def test_rows_with_a_different_cell_count_are_left_alone():
    ragged = "| a | b |\n|---|---|\n| only one |\n"
    assert format_text(ragged) == ragged


def test_pipes_without_a_delimiter_row_are_not_a_table():
    text = "| not | a table |\n| just | text |\n"
    assert format_text(text) == text


def test_check_reports_without_rewriting(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text(UNALIGNED, newline="")
    assert main(["--check", str(doc)]) == 1
    assert doc.read_text() == UNALIGNED
    assert "would reformat" in capsys.readouterr().out


def test_default_mode_rewrites_the_file(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text(UNALIGNED, newline="")
    assert main([str(doc)]) == 0
    assert doc.read_text() == ALIGNED


def test_check_passes_when_already_aligned(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text(ALIGNED, newline="")
    assert main(["--check", str(doc)]) == 0
