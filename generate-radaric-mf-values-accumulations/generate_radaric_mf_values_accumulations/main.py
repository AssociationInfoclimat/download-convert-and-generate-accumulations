import sys

from generate_radaric_mf_values_accumulations.arguments import parse_arguments
from generate_radaric_mf_values_accumulations.generation import (
    real_execute_from_arguments,
)


def main() -> None:
    arguments = parse_arguments(sys.argv[1:])
    real_execute_from_arguments(arguments)


if __name__ == "__main__":
    main()
