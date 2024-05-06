#! /bin/sh
git rm --cached udp
git rm --cached Dynamic-Band-Locking
git rm --cached quic_upload
git rm --cached tcp-upload
git rm .gitmodules
rm -rf udp/.git
rm -rf Dynamic-Band-Locking/.git
rm -rf Dynamic-Band-Locking/.gitignore
rm -rf quic_upload/.git
rm -rf tcp-upload/.git
git add --force udp
git add --force Dynamic-Band-Locking
git add --force quic_upload
git add --force tcp-upload
git commit -m "remove submodule"