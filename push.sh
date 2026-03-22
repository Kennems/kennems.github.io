#!/bin/zsh

echo "Please enter your commit message:"
read commitMessage

git add .
git commit -m "$commitMessage"
git push origin main

