Would you like to know more?
============================

End-to-End Example
------------------

An End-to-End example walkthrough of a tartufo scan and the process of purging the dirty evil passwords that somehow ended up in your code commits. We will use an additional tool: ``BFG`` (https://rtyley.github.io/bfg-repo-cleaner/, more on this later!). 

#. Use ``tartufo`` to scan your repository and find any secrets in its history!

   Use what you've learned to scan your repo!

   .. code-block:: console

      # Run Tartufo on your repo:
      GITHUBPROJECT="yourproject"
      GITHUBREPO="yourrepo.git"
      GITHUBADDRESS="github.com"
      tartufo git@${GITHUBADDRESS}:${GITHUBPROJECT}/${GITHUBREPO}
      # this will spit out a bunch of stuff and end with something like: Results have been saved in /tmp/tmp_jm3hyne
      TARTUFOSCANPATH="/tmp/tmp_jm3hyne"
      # this is the number of individual bad password hits tartufo has found:
      ls ${TARTUFOSCANPATH} | wc -l


#. Take results and create a "bad password" file. 

   This file will be used by ``BFG`` and replace these flagged "bad password" entries with ``***REMOVED***``. It is important that you read through this file to make sure there are not exceptions that you want to remove and exclude with tartufo!

   .. code-block:: console

      # Create a "Bad password" file
      BADSTRINGARR=`cat ${TARTUFOSCANPATH}/* | jq .strings_found | grep -v '\[' | grep -v '\]'`
      readarray -t PEWPEWPEWARR <<<"$BADSTRINGARR"
      # shows entires in array, may be larger than the earlier word count
      echo ${#PEWPEWPEWARR[@]};
      SORTED_UNIQUE_ENTRIES=($(echo "${PEWPEWPEWARR[@]}" | tr ' ' '\n' | sort -u | tr '\n' ' '))
      echo ${#SORTED_UNIQUE_ENTRIES[@]};
      printf "%s\n" "${SORTED_UNIQUE_ENTRIES[@]}" > badpwz.txt
      # remove leading/trailing quotes and trailing commas
      sed -i -e 's/\,$//g' -e 's/\"$//g' -e 's/^\"//g' badpwz.txt
      
   Now you have a "bad password" file! Take a look through it, see if anything is wrong, these values will be replaced in your code history


#. Cleanup repo using ``BFG`` and the above passwords file

   There's a very slick tool designed to cleanup git commit history called ``BFG``: https://rtyley.github.io/bfg-repo-cleaner/. By default ``BFG`` doesn't modify the contents of your latest commit on your master (or 'HEAD') branch, even though it will clean all the commits before it. This of course means if you have active code with "bad passwords" tartufo will still fail, but let's take the bulk of the old entries out first.

   .. code-block:: console

      # Cleanup with
      wget https://repo1.maven.org/maven2/com/madgag/bfg/1.13.0/bfg-1.13.0.jar
      git clone --mirror git@${GITHUBADDRESS}:${GITHUBPROJECT}/${GITHUBREPO}
      # Make a backup
      cp -r ${GITHUBREPO} backup_${GITHUBREPO}
      java -jar bfg-1.13.0.jar --replace-text badpwz.txt ${GITHUBREPO}
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
      To git@${GITHUBADDRESS}:yourproject/yourrepo.git
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
      error: failed to push some refs to 'git@${GITHUBADDRESS}:yourproject/yourrepo.git'
      (.venv) you@LTDV-you:~/tartufo/yourrepo.git$


   If you get the above error; It might actually be ok, re-run tartufo. Only if there are results that are not clean continue:

   .. code-block:: console

      # create a new blank repo, put the name below
      NEWGITHUBREPO="aws-jenkins-tartufoized.git"
      cd ../
      rm -rf ${GITHUBREPO}
      # Create a bare clone of the repository.
      git clone --bare git@${GITHUBADDRESS}:${GITHUBPROJECT}/${GITHUBREPO}
      # Mirror-push to the new repository (you can select the same repository)
      cd ${GITHUBREPO}
      git push --mirror git@${GITHUBADDRESS}:${GITHUBPROJECT}/${NEWGITHUBREPO}
      cd ..
      rm -rf ${GITHUBREPO}
      # bare clones are missing data, it is easier to re-clone the repo now that it does not have PRs
      git clone git@${GITHUBADDRESS}:${GITHUBPROJECT}/${NEWGITHUBREPO}
      # Now run tartufo/bfg 
      java -jar bfg-1.13.0.jar --replace-text badpwz.txt ${NEWGITHUBREPO}
      cd ${NEWGITHUBREPO}
      git reflog expire --expire=now --all && git gc --prune=now --aggressive
      git push
      # re-run tartufo on new repo
      tartufo git@${GITHUBADDRESS}:${GITHUBPROJECT}/${NEWGITHUBREPO}
      # should have very little (if any) output. check the newly outputed results
      ls /tmp/tmp_4i4c978 | wc -l
