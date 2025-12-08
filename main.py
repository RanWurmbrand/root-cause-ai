from core.rootcause_controller import ProjectRunner
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python project_runner.py /path/to/project [command]")
        exit(1)

    project_path = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else "npm test"

    runner = ProjectRunner(project_path, command)
    runner.run()
