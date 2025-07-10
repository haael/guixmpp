#!/usr/bin/python3


import os
import sys
import re
import pygraphviz as pgv
from collections import defaultdict
import subprocess

def parse_imports(file_path):
    """Parse Python file and extract import statements using import_deps."""
    try:
        result = subprocess.run(
            ['python3', '-m', 'import_deps', file_path],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the output to extract imported modules
        imports = set()
        for line in result.stdout.splitlines():
            if line.strip() and not line.startswith(file_path):
                imports.add(line.strip())

        return imports
    except subprocess.CalledProcessError as e:
        print(f"Error parsing imports for {file_path}: {e}")
        return set()

def build_import_graph(directory):
    """Build an import graph for Python files in the specified directory."""
    graph = defaultdict(set)

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                module_name = os.path.splitext(file)[0]
                imports = parse_imports(file_path)

                for import_module in imports:
                    graph[module_name].add(import_module)

    return graph

def visualize_import_graph(graph, output_file='import_graph.png'):
    """Visualize the import graph using pygraphviz."""
    dot = pgv.AGraph(directed=True)

    for module, imports in graph.items():
        for import_module in imports:
            dot.add_edge(module, import_module)

    dot.layout(prog='dot')
    dot.draw(output_file)
    print(f"Import graph saved to {output_file}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python import_graph.py <directory>")
        sys.exit(1)

    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory.")
        sys.exit(1)

    import_graph = build_import_graph(directory)
    visualize_import_graph(import_graph)

if __name__ == "__main__":
    main()
