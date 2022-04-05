from django.core.management import BaseCommand, call_command, CommandError
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.loader import MigrationLoader

from config import settings
from config.settings import INSTALLED_APPS
import subprocess
import os


def git_checkout(branch):
    return subprocess.run(['git', 'checkout', '-q', branch],
                          stderr=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          universal_newlines=True)


def git_current_branch():
    return subprocess.run(['git', 'branch', '--show-current'],
                          stdout=subprocess.PIPE,
                          universal_newlines=True).stdout.strip()


class Command(BaseCommand):
    help = "Migration-aware git checkout"

    def add_arguments(self, parser):
        parser.add_argument('branch', type=str, help='switch to this branch')
        parser.add_argument(
            '--plan', action='store_true',
            help='list the git and migrate commands without running them',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("checkout command requires debug mode")
        target_branch = options['branch']
        current_branch = git_current_branch()
        try_checkout = git_checkout(target_branch)
        if try_checkout.returncode != 0:
            raise CommandError(f"git checkout failed with the following message\n{try_checkout.stderr}")
        git_checkout(current_branch)
        connection = connections[DEFAULT_DB_ALIAS]
        loader = MigrationLoader(connection, ignore_no_migrations=True)
        graph = loader.graph

        target_migration_paths = []
        for app in INSTALLED_APPS:
            app_path = os.path.join(app, 'migrations', '')
            process = subprocess.run(['git', 'ls-tree', '--name-only', target_branch, app_path], stdout=subprocess.PIPE)
            target_migration_paths.extend(process.stdout.decode('utf-8').split('\n'))

        #  trim "/migrations" and ".py" from app_path and migration_file:
        target_migrations = [(app_path[:-11], migration_file[:-3]) for p in target_migration_paths
                             for app_path, migration_file in [os.path.split(p)]
                             if app_path and migration_file and migration_file != "__init__.py"]

        intersection_graph = MigrationGraph()
        for app, migration in graph.nodes:
            if (app, migration) in target_migrations:
                intersection_graph.add_node((app, migration), None)
        for parent in intersection_graph.nodes:
            for child in graph.node_map[parent].children:
                if parent not in target_migrations:
                    raise CommandError("Branches have apparently incompatible migration graphs")
                if child in intersection_graph.nodes:
                    intersection_graph.add_dependency(None, child, parent)
        if options['plan']:
            print("\nRoll back migrations on current branch:")
        for app_name in INSTALLED_APPS:
            current_leaves = {node for _, node in graph.leaf_nodes(app_name)}
            for _, node in intersection_graph.leaf_nodes(app_name):
                if node not in current_leaves:
                    if options['plan']:
                        print("python manage.py migrate", app_name, node)
                    else:
                        call_command("migrate", app_name, node)

        if options['plan']:
            print("\nSwitch to target branch:")
            print("git checkout", target_branch)
            print("\nMigrate to latest on target branch:")
            print("python manage.py migrate\n")
        else:
            git_checkout(target_branch)
            call_command("migrate")
