"""Tests for Makefile."""

import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import pytest
from pytest import MonkeyPatch


def get_source_makefile_path() -> Path:
    """Dynamically get the path to the source Makefile."""
    # start from the current file's directory
    current_dir = Path(__file__).resolve().parent

    # traverse upwards until you the 'Makefile' (assumed repo root)
    while current_dir.parent != current_dir:
        if (current_dir / "Makefile").exists():
            return current_dir  # found the source repository
        current_dir = current_dir.parent

    # coudln't find it
    raise FileNotFoundError("Could not find the Makefile in the source repository.")


@lru_cache(maxsize=1)
def get_cached_makefile_path() -> Path:
    """Retrieves and caches path to the Makefile in source repository."""
    return get_source_makefile_path() / "Makefile"


def run_make(
    target: str,
    dry_mode: bool = False,
    extra_args: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
    makefile_path: Optional[Path] = None,
) -> subprocess.CompletedProcess[str]:
    """Runs a Makefile target."""
    # default to source repo Makefile path if not provided
    if makefile_path is None:
        makefile_path = get_cached_makefile_path()

    # set default cwd to the current working directory if not provided
    if cwd is None:
        cwd = Path(".")

    # initial command string
    command = ["make", "-f", str(makefile_path)]

    # check for -n flag
    if dry_mode:
        command.append("-n")

    # add in target command
    command.append(target)

    # add any additional args
    if extra_args:
        command.extend(extra_args)

    # run process and get output
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)

    # done
    return result


def get_git_remote_url() -> str:
    """Helper function to get the remote URL of the repository."""
    try:
        # Run git command to get remote URL
        remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            universal_newlines=True,
        ).strip()

        # check if empy
        if not remote_url:
            return "Missing `origin` remote URL: No URL set for remote 'origin'."

        # normal
        return remote_url

    except subprocess.CalledProcessError:
        # Check remotes if 'origin' is missing
        try:
            remotes_list = subprocess.check_output(
                ["git", "remote", "-v"],
                universal_newlines=True,
            ).strip()

            # no origin
            return "Missing `origin` remote. " f"Available remotes: {remotes_list}"

        except subprocess.CalledProcessError:
            # no git repo
            return (
                "Error: Unable to fetch remote details. "
                "Ensure you are inside a valid Git repository."
            )


@pytest.fixture(scope="function")
def print_config_output() -> Dict[str, str]:
    """Fixture to get the output from the print-config target in Makefile."""
    result = run_make("print-config")

    # ensure the command ran successfully
    assert result.returncode == 0

    # parse the output from print-config and store as key-value pairs
    config_data = {}
    for line in result.stdout.splitlines():
        # only process lines with a key-value format (e.g., key: value)
        if ":" in line:
            key, value = line.split(":", 1)
            config_data[key.strip()] = value.strip()

    return config_data


@pytest.fixture(scope="function")
def current_directory(print_config_output: Dict[str, str]) -> Path:
    """Fixture to get the current dir from print-config output."""
    return Path(print_config_output["Current Directory"])


@pytest.mark.git
def test_git_installed() -> None:
    """Ensure that Git is installed and available."""
    assert shutil.which("git"), "Git is not installed or not found in PATH"


@pytest.mark.git
def test_git_remote_url() -> None:
    """Test that the git remote URL is valid and accessible."""
    remote_url = get_git_remote_url()

    # Check that the remote URL is not empty or invalid
    assert remote_url != "", "Git remote URL is empty!"

    # Check that it does not mention "Missing" unless the origin is missing
    assert (
        "Missing" not in remote_url or "origin" not in remote_url
    ), f"Unexpected missing remote: {remote_url}"

    # Check that the URL contains 'github.com'
    assert "github.com" in remote_url, f"Expected GitHub URL, but got: {remote_url}"


@pytest.mark.git
@pytest.mark.make
@pytest.mark.fixture
def test_no_empty_config_values(print_config_output: Dict[str, str]) -> None:
    """Test that none of the values in the print-config output are empty."""
    for value in print_config_output.values():
        assert (
            value != ""
        ), f"One of the config values is empty! Output:\n {print_config_output}"


@pytest.mark.git
@pytest.mark.make
@pytest.mark.fixture
def test_github_info_matches_docker_images(print_config_output: Dict[str, str]) -> None:
    """Test that GitHub user, repo name, and branch match the Docker images."""
    # extract values
    github_user = print_config_output["GitHub User"]
    repo_name = print_config_output["Repository Name"]
    git_branch = print_config_output["Git Branch"]

    # rebuild the expected Docker image names
    expected_image = f"ghcr.io/{github_user}/{repo_name}:{git_branch}"

    # extract the actual Docker images
    generated_image = print_config_output["Docker Image"]

    # assert that the rebuilt Docker images match the ones in the output
    assert expected_image == generated_image


@pytest.mark.git
@pytest.mark.make
def test_github_user_extraction_https() -> None:
    """Test GitHub username extraction from HTTPS URL."""
    # setup url
    remote_url = "https://github.com/User_Name/repo_name"
    result = run_make("test-github-user", extra_args=[f"REMOTE_URL={remote_url}"])

    # check exit value
    assert result.returncode == 0

    # cleanup output
    output = result.stdout.strip()

    # check user name
    assert output == "user_name"


@pytest.mark.git
@pytest.mark.make
def test_github_user_extraction_ssh() -> None:
    """Test GitHub username extraction from SSH URL."""
    # setup url
    remote_url = "git@github.com:User_Name/repo_name.git"
    result = run_make("test-github-user", extra_args=[f"REMOTE_URL={remote_url}"])

    # check exit value
    assert result.returncode == 0

    # cleaup output
    output = result.stdout.strip()

    # check user name
    assert output == "user_name"


@pytest.mark.git
@pytest.mark.make
def test_github_user_extraction_fails() -> None:
    """Test GitHub username extraction from invalid URL."""
    # setup url
    remote_url = "foo://bar@github.com/user/repo.git"
    result = run_make("test-github-user", extra_args=[f"REMOTE_URL={remote_url}"])

    # cleaup output
    output = result.stdout.strip()

    # error output
    assert "Invalid" in output
    assert remote_url in output


@pytest.mark.make
def test_run_make_invalid_target() -> None:
    """Confirm missing target fails."""
    # run make on missing target
    result = run_make("nonexistent_target", dry_mode=True)

    # check correct error
    assert result.returncode != 0
    assert "No rule to make target" in result.stderr


@pytest.mark.make
def test_run_make_dry_mode(monkeypatch: MonkeyPatch) -> None:
    """Test the behavior of `run_make` with dry-run mode enabled."""

    def mock_subprocess_run(
        command: List[str], *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> subprocess.CompletedProcess[str]:
        """Mock function for subprocess.run to simulate command execution."""
        # check that "-n" (dry-run flag) is in the command list
        assert "-n" in command

        # check that the target name "build" is in the command list
        assert "build" in command

        # simulate a successful subprocess result
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    # replace subprocess.run with our mock function during the test
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    # call run_make with dry_mode set to True
    run_make("build", dry_mode=True)


@pytest.mark.make
def test_run_make_with_extra_args(monkeypatch: MonkeyPatch) -> None:
    """Test the `run_make` function with additional arguments."""

    def mock_subprocess_run(
        command: List[str], *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> subprocess.CompletedProcess[str]:
        """Mock function for subprocess.run to simulate command execution."""
        # check that the extra arguments are in the command list
        assert "--jobs" in command
        assert "4" in command
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    # replace subprocess.run with our mock function during the test
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    # call run_make with extra_args set to ['--jobs', '4']
    run_make("build", extra_args=["--jobs", "4"])


@pytest.mark.make
def test_check_docker_dry_run() -> None:
    """Test `check-docker` make target executes the expected command."""
    result = run_make("check-docker", dry_mode=True)

    # verify that the expected command appears in the dry run output
    assert "docker --version" in result.stdout
    assert result.returncode == 0


@pytest.mark.make
def test_check_deps_tests_without_notty_defined() -> None:
    """Test that NOTTY is correctly handled when not set."""
    result = run_make("check-deps", dry_mode=True)
    assert result.returncode == 0
    assert "-it" in result.stdout  # Ensure -it is included


@pytest.mark.make
def test_check_deps_tests_with_notty() -> None:
    """Test that NOTTY is correctly handled in check-deps-tests."""
    result = run_make("check-deps", extra_args=["NOTTY=true"], dry_mode=True)
    assert result.returncode == 0
    assert "-i" in result.stdout
    assert "-it" not in result.stdout  # Ensure -it is not included


@pytest.mark.make
def test_check_deps_tests_without_notty() -> None:
    """Test that NOTTY is correctly handled when false."""
    result = run_make("check-deps", extra_args=["NOTTY=false"], dry_mode=True)
    assert result.returncode == 0
    assert "-it" in result.stdout  # Ensure -it is included


@pytest.mark.make
def test_build_tests_no_options() -> None:
    """Test build target without DCKR_PULL or DCKR_NOCACHE options."""
    result = run_make("build", dry_mode=True)

    # Check that docker pull/build is in command, but no --no-cache flag
    assert "docker pull" in result.stdout
    assert "docker build" in result.stdout
    assert "--no-cache" not in result.stdout


@pytest.mark.make
def test_build_tests_with_nocache() -> None:
    """Test the build target with DCKR_NOCACHE option."""
    result = run_make("build", dry_mode=True, extra_args=["DCKR_NOCACHE=true"])

    # Check that --no-cache flag is passed to docker build
    assert "docker build" in result.stdout
    assert "--no-cache" in result.stdout
    assert "docker pull" in result.stdout


@pytest.mark.make
def test_build_tests_with_no_pull() -> None:
    """Test build target with no DCKR_PULL."""
    result = run_make("build", dry_mode=True, extra_args=["DCKR_PULL=false"])

    # check that docker pull not included in the output
    assert "docker pull" not in result.stdout
    assert "docker build" in result.stdout
    assert "--no-cache" not in result.stdout


@pytest.mark.make
def test_use_vol_default() -> None:
    """Test that volume is mounted by default."""
    # run the make command with default environment (USE_VOL=true)
    result = run_make("pytest", dry_mode=True)

    # assert that the expected flag "-v" is present in the result
    assert result.returncode == 0
    assert "-v" in result.stdout


@pytest.mark.make
def test_use_vol_off(current_directory: Path) -> None:
    """Test that volume is mounted by default."""
    # run the make command with default environment (USE_VOL=true)
    result = run_make("pytest", dry_mode=True, extra_args=["USE_VOL=false"])

    # assert that the expected flag "-v" is present in the result
    assert result.returncode == 0
    assert "-v" not in result.stdout
    assert str(current_directory) not in result.stdout


@pytest.mark.make
def test_use_usr_default() -> None:
    """Test that `--user` is enabled by default in the Makefile."""
    # Run the make command with default environment (USE_USR=true)
    result = run_make("pytest", dry_mode=True)

    # Assert that the expected flag "-u" is present in the result
    assert "--user" in result.stdout


@pytest.mark.make
def test_use_usr_off() -> None:
    """Test that `--user` is missing with USE_USR=false."""
    # Run the make command with default environment (USE_USR=true)
    result = run_make("pytest", dry_mode=True, extra_args=["USE_USR=false"])

    # Assert that the expected flag "-u" is present in the result
    assert "--user" not in result.stdout


@pytest.mark.make
def test_check_workdir_matches_dckrsrc(print_config_output: Dict[str, str]) -> None:
    """Test that the working directory inside the container matches DCKRSRC."""
    # set the expected working directory
    expected_workdir = f"/usr/local/src/{print_config_output['Repository Name']}"

    # pull actual DCKRSRC from config output
    actual_workdir = print_config_output["Docker Source Path"]

    # make sure they match
    assert expected_workdir == actual_workdir
