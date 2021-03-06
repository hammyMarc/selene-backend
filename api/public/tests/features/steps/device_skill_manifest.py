# Mycroft Server - Backend
# Copyright (C) 2019 Mycroft AI Inc
# SPDX-License-Identifier: 	AGPL-3.0-or-later
#
# This file is part of the Mycroft Server.
#
# The Mycroft Server is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import json
from datetime import datetime

from behave import when, then
from hamcrest import assert_that, equal_to, is_in, is_, none, not_none, not_

from selene.data.device import DeviceSkillRepository, ManifestSkill
from selene.data.skill import SkillRepository, Skill


def _build_manifest_upload(manifest_skills):
    upload_skills = []
    for skill in manifest_skills:
        upload_skills.append(
            dict(
                name="test-skill-name",
                origin=skill.install_method,
                beta=False,
                status="active",
                installed=skill.install_ts.timestamp(),
                updated=skill.update_ts.timestamp(),
                installation=skill.install_status,
                skill_gid=skill.skill_gid,
            )
        )
    return {
        "blacklist": [],
        "version": 1,
        "skills": upload_skills
    }


@when('a device uploads a skill manifest without changes')
def upload_unchanged_skill_manifest(context):
    skill_manifest = _build_manifest_upload([context.manifest_skill])
    _upload_skill_manifest(context, skill_manifest)


@when('a device uploads a skill manifest with an updated skill')
def upload_unchanged_skill_manifest(context):
    skill_manifest = _build_manifest_upload([context.manifest_skill])
    context.update_ts = datetime.utcnow().timestamp()
    skill_manifest['skills'][0]['updated'] = context.update_ts
    _upload_skill_manifest(context, skill_manifest)


@when('a device uploads a skill manifest with a deleted skill')
def upload_unchanged_skill_manifest(context):
    skill_manifest = _build_manifest_upload([])
    _upload_skill_manifest(context, skill_manifest)


@when('a device uploads a skill manifest with a deleted device-specific skill')
def upload_skill_manifest_no_device_specific(context):
    skill_manifest = _build_manifest_upload([context.manifest_skill])
    _upload_skill_manifest(context, skill_manifest)


@when('a device uploads a skill manifest with a new skill')
def upload_unchanged_skill_manifest(context):
    context.new_skill = Skill(skill_gid='new-test-skill|19.02')
    context.new_manifest_skill = ManifestSkill(
        device_id=context.device_id,
        install_method='test_install_method',
        install_status='test_install_status',
        skill_gid=context.new_skill.skill_gid,
        install_ts=datetime.utcnow(),
        update_ts=datetime.utcnow()
    )

    skill_manifest = _build_manifest_upload(
        [context.manifest_skill, context.new_manifest_skill]
    )
    _upload_skill_manifest(context, skill_manifest)


@when('a device uploads a malformed skill manifest')
def upload_unchanged_skill_manifest(context):
    skill_manifest = _build_manifest_upload([context.manifest_skill])
    del(skill_manifest['skills'][0]['name'])
    _upload_skill_manifest(context, skill_manifest)


def _upload_skill_manifest(context, skill_manifest):
    context.response = context.client.put(
        '/v1/device/{device_id}/skillJson'.format(device_id=context.device_id),
        data=json.dumps(skill_manifest),
        content_type='application/json',
        headers=context.request_header
    )


@then('the skill manifest on the database is unchanged')
def get_unchanged_skill_manifest(context):
    device_skill_repo = DeviceSkillRepository(context.db)
    skill_manifest = device_skill_repo.get_skill_manifest_for_device(
        context.device_id
    )
    assert_that(len(skill_manifest), equal_to(1))
    manifest_skill = skill_manifest[0]
    assert_that(manifest_skill, equal_to(context.manifest_skill))


@then('the skill manifest on the database is updated')
def get_updated_skill_manifest(context):
    device_skill_repo = DeviceSkillRepository(context.db)
    skill_manifest = device_skill_repo.get_skill_manifest_for_device(
        context.device_id
    )
    assert_that(len(skill_manifest), equal_to(1))
    manifest_skill = skill_manifest[0]
    assert_that(manifest_skill, not_(equal_to(context.manifest_skill)))
    manifest_skill.update_ts = context.update_ts
    assert_that(manifest_skill, (equal_to(context.manifest_skill)))


@then('the skill is removed from the manifest on the database')
def get_empty_skill_manifest(context):
    device_skill_repo = DeviceSkillRepository(context.db)
    skill_manifest = device_skill_repo.get_skill_manifest_for_device(
        context.device_id
    )
    assert_that(len(skill_manifest), equal_to(0))


@then('the device-specific skill is removed from the manifest on the database')
def get_skill_manifest_no_device_specific(context):
    device_skill_repo = DeviceSkillRepository(context.db)
    skill_manifest = device_skill_repo.get_skill_manifest_for_device(
        context.device_id
    )
    assert_that(len(skill_manifest), equal_to(1))
    remaining_skill = skill_manifest[0]
    assert_that(
        remaining_skill.skill_gid,
        not_(equal_to(context.device_specific_skill.skill_gid))
    )


@then('the device-specific skill is removed from the database')
def ensure_device_specific_skill_removed(context):
    skill_repo = SkillRepository(context.db)
    skill = skill_repo.get_skill_by_global_id(
        context.device_specific_skill.skill_gid
    )
    assert_that(skill, is_(none()))


@then('the skill is added to the manifest on the database')
def get_skill_manifest_new_skill(context):
    device_skill_repo = DeviceSkillRepository(context.db)
    skill_manifest = device_skill_repo.get_skill_manifest_for_device(
        context.device_id
    )
    assert_that(len(skill_manifest), equal_to(2))
    assert_that(context.manifest_skill, is_in(skill_manifest))

    # the device_skill id is not part of the request data so clear it out
    for manifest_skill in skill_manifest:
        if manifest_skill.skill_gid == context.new_skill.skill_gid:
            manifest_skill.id = None
            manifest_skill.skill_id = None
    assert_that(context.new_manifest_skill, is_in(skill_manifest))


@then('the skill is added to the database')
def get_new_skill(context):
    skill_repo = SkillRepository(context.db)
    skill = skill_repo.get_skill_by_global_id(
        context.new_skill.skill_gid
    )
    assert_that(skill, is_(not_none()))
