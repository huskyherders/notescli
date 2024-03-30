#!/usr/bin/env python3.10
import argparse
import os
import glob
import json
import click
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class NotesCfg:
    dirpath: str
    remote: str
    signedCommits: bool = False


#
# Git
#
def git_clone(remote:str, dirpath:str):
    """
    Clone a remote repository to a local directory
    """
    cmd = f"git clone {remote} {dirpath}"
    os.system(cmd)

def git_init(dirpath:str):
    """
    Initialize a local directory as a git repository
    """
    cmd = f"git init {dirpath}"
    os.system(cmd)

def git_add(dirpath:str, filename:str):
    """
    Add a file to the git repository
    """
    cmd = f"git -C {dirpath} add {filename}"
    os.system(cmd)

def git_commit(dirpath:str, message:str, signed:bool=False):
    """
    Commit changes to the git repository
    """
    cmd = f"git -C {dirpath} commit -m '{message}'"
    if signed:
        cmd += " -S"
    os.system(cmd)

def git_push(dirpath:str):
    """
    Push changes to the remote repository
    """
    cmd = f"git -C {dirpath} push"
    os.system(cmd)

#
# Configuration 
#

def get_cfg()->NotesCfg:
    """
    Read the config (if it exists) and return a NotesCfg object
    """
    cfg = NotesCfg(dirpath=".", remote="")
    # Get path to this file
    cfgFile = Path(os.path.realpath(__file__))
    cfgFile = cfgFile.parent / ".notescfg"
    if os.path.exists(cfgFile):
        with open(cfgFile, "r") as fr:
            data = json.load(fr)
            cfg = NotesCfg(**data)
    return cfg

def setup(cfg:NotesCfg):
    """
    Write the config to a file
    """
    # Initialize the git repository
    if cfg.remote:
        git_clone(cfg.remote, cfg.dirpath)
    else:
        # Create local directory only
        if not os.path.exists(cfg.dirpath):
            os.makedirs(cfg.dirpath)
        git_init(cfg.dirpath)
    # Check if the directory is empty
    files = glob.glob(f"{cfg.dirpath}/*")
    if len(files) > 0:
        # Setup initial files for git 
        os.makedirs(f"{cfg.dirpath}/uncategorized")
    if not os.path.exists(f"{cfg.dirpath}/tags.json"):
        new_tagfile(cfg.dirpath)
        git_add(cfg.dirpath, "tags.json")
        git_commit(cfg.dirpath, "Add initial tags file")
    # Save cfg
    cfgFile = Path(os.path.realpath(__file__))
    cfgFile = cfgFile.parent / ".notescfg"
    with open(cfgFile, "w") as fw:
        json.dump(asdict(cfg), fw)

def new_tagfile(dirpath:str):
    """
    Create a new tag file
    """
    dfltFile = Path(os.path.realpath(__file__))
    dfltFile = dfltFile.parent / "defaulttags.json"
    with open(dfltFile, "r") as fr:
        DEFAULT_TAGS = json.load(fr)
    
    with open(f"{dirpath}/tags.json", "w") as f:
        json.dump(DEFAULT_TAGS, f)

def get_tags(dirpath:str):
    """
    Get the tags from the tags file
    """
    if not os.path.exists(f"{dirpath}/tags.json"):
        new_tagfile(dirpath)
    with open(f"{dirpath}/tags.json", "r") as f:
        tags = json.load(f)
    return tags

def update_tags(cfg:NotesCfg, fn:str, fileTags:list, tags:dict, updated:bool):
    """
    Update the tags file
    """
    dirpath = Path(cfg.dirpath)
    if updated:
        tagFile = dirpath / "tags.json"
        with open(tagFile, "w") as f:
            json.dump(tags, f)
        git_add(cfg.dirpath, str(tagFile.relative_to(cfg.dirpath)))
    # Update the file tags
    filetags = Path(cfg.dirpath) / "filetags.json"
    with open(filetags, "w") as f:
        json.dump(fileTags, f)
    git_add(cfg.dirpath, str(filetags.relative_to(cfg.dirpath)))
        

#
# New Notes
#

def get_note(title:str):
    """Open an editor for user to write a note"""
    message = click.edit(f"# {title}\n\n")
    return message

def new(title:str, cfg:NotesCfg):
    """Create a new note"""
    note = get_note(title.title())
    if note:
        fn = title.lower().replace(" ", "_").replace("/", "-").replace(".", "-")
        # Figure out topics and tags
        topics = fn.split("_")
        tags = get_tags(cfg.dirpath)
        fileTags = []
        for topic in topics:
            if topic in tags["topics"]:
                fileTags.append(topic)
        # Allow user to add more tags with input prompt
        updated = False
        print("Tags: ", fileTags)
        newtag = input("Add a tag: ")
        while newtag:
            if newtag not in tags['topics']:
                tags['topics'].append(newtag)
                updated = True
            if newtag in fileTags:
                fileTags.remove(newtag)
            else:
                fileTags.append(newtag)
            newtag = input("Add a tag: ")
        update_tags(cfg, fn, fileTags, tags, updated)
        # Write the notes
        if len(fileTags) > 0:
            topicDir = fileTags[0]
        else:
            topicDir = "uncategorized"
        topicDirPath = Path(f"{cfg.dirpath}") / topicDir
        if not os.path.exists(topicDirPath):
            os.makedirs(topicDirPath)

        filePath = topicDirPath / f"{fn}.md"
        with open(filePath, "w") as f:
            f.write(note)

        # Add the file to the git repository
        gitFile = filePath.relative_to(cfg.dirpath)
        git_add(cfg.dirpath, str(gitFile))
        git_commit(cfg.dirpath, f"Add {title}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create a new TIL file')
    parser.add_argument('--nosync', action='store_true', help='Do not sync with remote')
    subparser = parser.add_subparsers(help='sub-commonds', dest='command')
    newParser = subparser.add_parser('new', help='Create a new note')
    newParser.add_argument('titleNew', type=str, help='Title of the TIL')
    
    searchParser = subparser.add_parser('search', help='Search for a note or topic')
    searchParser.add_argument('--topic', type=str, help='Search for a topic')
    searchParser.add_argument('--title', type=str, help='Search for a title')
    searchParser.add_argument('--tag', type=str, help='Search for a tag')

    modifyParser = subparser.add_parser('modify', help='Modify a note')
    modifyParser.add_argument('titleModify', type=str, help='Title of the TIL')

    deleteParser = subparser.add_parser('delete', help='Delete a note')
    deleteParser.add_argument('titleDelete', type=str, help='Title of the TIL')

    repoParser = subparser.add_parser('repo', help='Initialize or change the TIL repository')
    repoParser.add_argument('dirpath', type=str, help='Path to local directory for the TIL repository')
    repoParser.add_argument('--remote', type=str, help='URL of the remote repository')
    args = parser.parse_args()

    print(args)
    cfg = get_cfg()
    if args.command == 'new':
        new(args.titleNew, cfg)
        if not args.nosync:
            git_push(cfg.dirpath)
    elif args.command == 'repo':
        cfg.dirpath = args.dirpath
        if args.remote:
            cfg.remote = args.remote
        setup(cfg)
        if not args.nosync:
            git_push(cfg.dirpath)


