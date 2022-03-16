# djangit
Django-enhanced versions of classic git commands

To install djangit, you will need ssh credentials for github.  Run

    pip install git+ssh://git@github.com/zagaran/djangit.git

If the clone fails
because of missing credentials, you can generate and add a new
ssh key for github by following the instructions here: https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent
.

Once djangit is installed, you can use djangit by adding management commands.  Djangit currently
only supplies one command, which is "checkout".  To install this command, make a new file

    django_app/management/commands/checkout.py

with the following contents 

    from djangit.checkout import Command

Now the "checkout" command will be available as a django management command.

## Djangit checkout
The "checkout" command functions like git checkout, but also takes care of django migrations.  The algorithm
identifies the largest migration subtree that is common to the two branches.  It then migrates down to this
core subtree, switches branches, and then migrates back up on the new branch.  The idea is to leave all common
migrations in place while interacting with branch-specific migrations only while that branch is checked out.

To use the command, run

    python manage.py checkout git_branch_name --plan

This will show you the commands that checkout plans to run.  If you like what you see, then 
remove the --plan flag:

    python manage.py checkout git_branch_name --plan


