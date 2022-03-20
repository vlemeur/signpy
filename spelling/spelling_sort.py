"""Sort custom dictionary for spell checker pyenchant."""

from pathlib import Path

DEFAULT_FILE_PATH = Path(__file__).parent / "spelling.txt"


def sorting(filename: Path = DEFAULT_FILE_PATH):
    """Sort a text file inplace with a header on top of file.

    Parameters
    ----------
    filename : Path
        Path to the text file, by default DEFAULT_FILE_PATH
    """
    with open(filename, "r") as lines:
        sections = {}
        section = None
        for line in lines:
            if "#" in line:
                section = line
                sections[section] = []
            else:
                sections[section].append(line)

        for section, words in sections.items():
            sections[section] = sorted(set(words))

        with open(filename, "w") as outfile:
            for section, words in sections.items():
                outfile.write(section)
                outfile.writelines(words)
                if section != list(sections.keys())[-1]:
                    outfile.write("\n")


if __name__ == "__main__":
    sorting()
