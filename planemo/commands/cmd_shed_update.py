"""Module describing the planemo ``shed_update`` command."""
import sys

import click

from planemo.cli import command_function
from planemo import options
from planemo import shed
from planemo.io import info, error
from planemo.reports import build_report
from planemo.io import captured_io_for_xunit


@click.command("shed_update")
@options.report_xunit()
@options.shed_publish_options()
@options.shed_upload_options()
@options.shed_skip_upload()
@options.shed_skip_metadata()
@command_function
def cli(ctx, paths, **kwds):
    """Update repository in shed from a ``.shed.yml`` file.

    By default this command will update both repository metadata
    from ``.shed.yml`` and upload new contents from the repository
    directory.

    ::

        % planemo shed_update

    This will update the main tool shed with the repository defined
    by a ``.shed.yml`` file in the current working directory. Both
    the location of the ``.shed.yml`` and the tool shed to upload to
    can be easily configured. For instance, the following command can
    be used if ``.shed.yml`` if contained in ``path/to/repo`` and the
    desire is to update the test tool shed.

    ::

        % planemo shed_update --shed_target testtoolshed path/to/repo

    Another important option is ``--check_diff`` - this doesn't affect the
    updating of shed metadata but it will check for differences before
    uploading new contents to the tool shed. This may important because the
    tool shed will automatically populate certain attributes in tool shed
    artifact files (such as ``tool_dependencies.xml``) and this may
    cause unwanted installable revisions to be created when there are no
    important changes.

    The lower-level ``shed_upload`` command should be used instead if
    the repository doesn't define complete metadata in a ``.shed.yml``.
    """
    # In a little bit of cheating, we're defining this variable here to collect
    # a "report" on the shed_update command
    collected_data = {
        'results': {
            'total': 0,
            'errors': 0,
            'failures': 0,
            'skips': 0,
        },
        'suitename': 'update',
        'tests': [],
    }

    shed_context = shed.get_shed_context(ctx, **kwds)

    def update(realized_repository):
        collected_data['results']['total'] += 1
        skip_upload = kwds["skip_upload"]
        skip_metadata = kwds["skip_metadata"]
        upload_ret_code = 0
        upload_ok = True

        captured_io = {}
        if not skip_upload:
            with captured_io_for_xunit(kwds, captured_io):
                upload_ret_code = shed.upload_repository(
                    ctx, realized_repository, **kwds
                )
                upload_ok = not upload_ret_code

        repo_result = {
            'classname': realized_repository.name,
            'time': captured_io.get("time", None),
            'name': 'shed-update',
            'stdout': captured_io.get("stdout", None),
            'stderr': captured_io.get("stderr", None),
        }

        # Now that we've uploaded (or skipped appropriately), collect results.
        if upload_ret_code == 2:
            collected_data['results']['failures'] += 1
            repo_result.update({
                'errorType': 'FailedUpdate',
                'errorMessage': 'Failed to update repository as it does not exist in target ToolShed',
            })
            collected_data['tests'].append(repo_result)
            error("Failed to update repository it does not exist "
                  "in target ToolShed.")
            return upload_ret_code

        exit = 0
        metadata_ok = True
        if not skip_metadata:
            repo_id = shed.handle_force_create(realized_repository, ctx, shed_context, **kwds)
            # failing to create the repo, give up
            if repo_id is None:
                exit = shed.report_non_existent_repository(realized_repository)
                metadata_ok = False
            else:
                metadata_ok = realized_repository.update(ctx, shed_context, repo_id)
        else:
            info("Skipping repository metadata update.")

        if not metadata_ok:
            error("Failed to update repository metadata.")

        if metadata_ok and upload_ok:
            pass
        elif upload_ok:
            collected_data['results']['skips'] += 1
            repo_result.update({
                'errorType': 'FailedMetadata',
                'errorMessage': 'Failed to update repository metadata',
            })
            if not skip_upload:
                error("Repo updated but metadata was not.")
            exit = exit or 1
        else:
            collected_data['results']['failures'] += 1
            repo_result.update({
                'errorType': 'FailedUpdate',
                'errorMessage': 'Failed to update repository',
            })
            error("Failed to update a repository.")
            exit = exit or 1
        collected_data['tests'].append(repo_result)
        return exit

    exit_code = shed.for_each_repository(ctx, update, paths, **kwds)

    if kwds.get('report_xunit', False):
        with open(kwds['report_xunit'], 'w') as handle:
            handle.write(build_report.template_data(
                collected_data, template_name='xunit.tpl')
                .encode('ascii', 'xmlcharrefreplace'))

    sys.exit(exit_code)
