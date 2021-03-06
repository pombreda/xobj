#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


SUBDIRS = py as3


build: default-build

install: default-install

clean: default-clean

test: default-test

forcetag:
	hg tag -f xobj-$(VERSION)

tag:
	hg tag xobj-$(VERSION)



dist: archive

archive-snapshot:
	hg archive --exclude .hgignore -t tbz2 xobj-$$(hg id -i).tar.bz2

archive:
	hg archive --exclude .hgignore -t tbz2 xobj-$(VERSION).tar.bz2


export TOPDIR=$(shell pwd)
include $(TOPDIR)/Make.rules
include $(TOPDIR)/Make.defs
