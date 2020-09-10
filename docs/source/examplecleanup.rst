Would you like to know more?
============================

End-to-End Example
------------------

An End-to-End example walkthrough of a tartufo scan and the process of purging the dirty evil passwords that somehow ended up in your code commits. We will use an additional tool: ``BFG`` (https://rtyley.github.io/bfg-repo-cleaner/, more on this later!). 


#. Setup poetry if you want to use the most recent build

   This project uses [Poetry] to manage its dependencies and do a lot of the heavy lifting. So you'll need to clone the tartufo repo and setup poetry!


   .. code-block:: console

      git clone git@github.com:godaddy/tartufo.git
      

   Next: [Install Poetry]  

   Finally: Run ``poetry install``


#. Clone your repo!

   Select and clone the repo you want to run tartufo on

   .. code-block:: console

      # Clone your repo, variables used later:
      GITHUBPROJECT="yourproject"
      GITHUBREPO="myrepo.git"
      GITHUBADDRESS="github.com"
      git clone --mirror git@${GITHUBADDRESS}:${GITHUBPROJECT}/${GITHUBREPO}


#. Use ``tartufo`` to scan your repository and find any secrets in its history!

   Use what you've learned to scan your repo!

   .. code-block:: console

      # Run Tartufo on your repo and create a list of high entropy items to remove:
      poetry run tartufo --regex --json --cleanup ${GITHUBREPO} | jq -r '.found_issues[].matched_string' | sort -u > remove.txt

   Now you have a "bad password" file! Take a look through it, see if anything is wrong. This file will be used by ``BFG`` and replace these flagged "bad password" entries with ``***REMOVED***``. It is important that you read through this file to make sure there are not exceptions that you want to remove and exclude with tartufo!


#. Cleanup repo using ``BFG`` and the above remove.txt file

   There's a very slick tool designed to cleanup git commit history called ``BFG``: https://rtyley.github.io/bfg-repo-cleaner/. By default ``BFG`` doesn't modify the contents of your latest commit on your master (or 'HEAD') branch, even though it will clean all the commits before it. This of course means if you have active code with "bad passwords" tartufo will still fail, but let's take the bulk of the old entries out first.

   .. code-block:: console

      # Cleanup with BFG
      wget https://repo1.maven.org/maven2/com/madgag/bfg/1.13.0/bfg-1.13.0.jar
      # Make a backup
      cp -r ${GITHUBREPO} backup_${GITHUBREPO}

      do java -jar bfg-1.13.0.jar --replace-text remove.txt ${GITHUBREPO}


#. Uh Oh!

   Occasionally the results will be to big to process all at once. If that happens simply split up the results and loop through them.

   .. code-block:: console

      # occasionally the results will be to big to process all at once
      split -l 200 remove.txt
      for f in x*; do java -jar bfg-1.13.0.jar --replace-text $f ${GITHUBREPO}; done


#. Proceed with cleanup/audit

   Now you have removed the low hanging fruit, it's time to look at the tough stuff

   .. code-block:: console

      #run tartufo again to check for icky code straglers in active code
      leftovers=`poetry run tartufo --regex --no-cleanup ${GITHUBREPO}`
      tmppath=`echo -e "$leftovers" | tail -n1 | awk '{print $6}'`
      #look through the remaining strings, if there's anything that looks like it shouldn't be there, dig into it and clear it out
      cat ${tmppath}/* | jq '. | " \(.file_path) \(.matched_string) \(.signature)"' | sort -u


#. Once you are happy with the data that is being stored, time to commit the changes back up!

   Note: This does a force push

   .. code-block:: console

      cd ${GITHUBREPO}
      git reflog expire --expire=now --all && git gc --prune=now --aggressive
      git push


#. Danger Will Robinson, Danger! 

   You MAY get an error (example error below), if so keep reading!

   .. code-block:: console

      (.venv) you@LTDV-you:~/tartufo/yourrepo.git$ git push
      Counting objects: 1014, done.
      Delta compression using up to 8 threads.
      Compressing objects: 100% (359/359), done.
      Writing objects: 100% (1014/1014), 130.35 KiB | 0 bytes/s, done.
      Total 1014 (delta 662), reused 964 (delta 638)
      remote: Resolving deltas: 100% (662/662), completed with 24 local objects.
      To git@GITHUBADDRESS:yourproject/yourrepo.git
       + 56f7476...c76ed2b master -> master (forced update)
       ! [remote rejected] refs/pull/1/head -> refs/pull/1/head (deny updating a hidden ref)
       ! [remote rejected] refs/pull/2/head -> refs/pull/2/head (deny updating a hidden ref)
       ! [remote rejected] refs/pull/3/head -> refs/pull/3/head (deny updating a hidden ref)
       ! [remote rejected] refs/pull/4/head -> refs/pull/4/head (deny updating a hidden ref)
       ! [remote rejected] refs/pull/5/head -> refs/pull/5/head (deny updating a hidden ref)
       ! [remote rejected] refs/pull/6/head -> refs/pull/6/head (deny updating a hidden ref)
       ! [remote rejected] refs/pull/7/head -> refs/pull/7/head (deny updating a hidden ref)
       ! [remote rejected] refs/pull/8/head -> refs/pull/8/head (deny updating a hidden ref)
       ! [remote rejected] refs/pull/9/head -> refs/pull/9/head (deny updating a hidden ref)
      error: failed to push some refs to 'git@GITHUBADDRESS:yourproject/yourrepo.git'
      (.venv) you@LTDV-you:~/tartufo/yourrepo.git$


   If you get the above error; It might actually be ok, re-run tartufo from master. Only if there are results that are not clean continue. Please note, this solution will remove PR history (but not commit history):

   .. code-block:: console

      # create a new blank repo, put the name below
      NEWGITHUBREPO="aws-jenkins-tartufoized.git"
      cd ../
      rm -rf ${GITHUBREPO}
      # Create a bare clone of the repository.
      git clone --bare git@${GITHUBADDRESS}:${GITHUBPROJECT}/${GITHUBREPO}
      # Mirror-push to the new temporary repository 
      cd ${GITHUBREPO}
      git push --mirror git@${GITHUBADDRESS}:${GITHUBPROJECT}/${NEWGITHUBREPO}
      cd ..
      rm -rf ${GITHUBREPO}
      # bare clones are missing data, it is easier to re-clone the repo now that it does not have PRs
      git clone git@${GITHUBADDRESS}:${GITHUBPROJECT}/${NEWGITHUBREPO}
      # Now run bfg 
      java -jar bfg-1.13.0.jar --replace-text remove.txt ${NEWGITHUBREPO}
      cd ${NEWGITHUBREPO}
      git reflog expire --expire=now --all && git gc --prune=now --aggressive
      git push
      # re-run tartufo on new repo
      tartufo git@${GITHUBADDRESS}:${GITHUBPROJECT}/${NEWGITHUBREPO}
      # should have very little (if any) output. check the newly outputed results in the given tmp folder
      ls /tmp/tmp_4i4c978 | wc -l


Additional Resources
------------------

[Install Poetry]: https://python-poetry.org/docs/#installation

[Poetry]: https://python-poetry.org/
