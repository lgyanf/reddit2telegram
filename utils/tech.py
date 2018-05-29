#encoding:utf-8

import importlib
import csv
import yaml
import datetime
import random

import pymongo


def get_dev_channel(config_filename=None):
    if config_filename is None:
        config_filename = 'configs/prod.yml'
    with open(config_filename) as config_file:
        config = yaml.load(config_file.read())
        return config['telegram']['dev_chat']


def get_all_submodules(config_filename=None):
    if config_filename is None:
        config_filename = 'configs/prod.yml'
    with open(config_filename) as config_file:
        config = yaml.load(config_file.read())
        all_submodules = set()
        with open(config['cron_file']) as tsv_file:
            tsv_reader = csv.DictReader(tsv_file, delimiter='\t')
            for row in tsv_reader:
                submodule_name = row['submodule_name']
                all_submodules.add(submodule_name)
        return all_submodules


def get_all_public_channels(config_filename=None):
    all_submodules = get_all_submodules(config_filename)
    channels_list = list()
    for submodule_name in all_submodules:
        submodule = importlib.import_module('channels.{}.app'.format(submodule_name))
        channel_name = submodule.t_channel
        if ('@' in channel_name) and (channel_name not in ['@r_channels_test', '@r_channels']):
            channels_list.append(channel_name)
    return channels_list


def generate_list_of_channels(channels_list, random_permutation=False):
    if random_permutation:
        channels_list = random.sample(channels_list, k=len(channels_list))
    list_of_channels = ['{n}. {channel}'.format(n=str(i + 1).zfill(2), channel=channel)
                        for i, channel in enumerate(channels_list)]
    return list_of_channels


def get_active_period(r2t, channel_name):
    min_cursor = r2t.stats.find({'channel' : channel_name.lower()}).sort([('ts', pymongo.ASCENDING)]).limit(1)
    min_ts = min_cursor.next()['ts']
    max_cursor = r2t.stats.find({'channel' : channel_name.lower()}).sort([('ts', pymongo.DESCENDING)]).limit(1)
    max_ts = max_cursor.next()['ts']
    diff = max_ts - min_ts
    return diff.days


def get_newly_active(r2t, channels_list):
    newly_active = list()
    for channel in channels_list:
        days_active = get_active_period(r2t, channel)
        if days_active <= 31:
            newly_active.append(channel)
    return newly_active


def get_top_growers_for_last_week(r2t, channels_list):
    top_growers = dict()
    one_week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    for channel in channels_list:
        week_ago_cursor = r2t.stats.find({
            'channel': channel.lower(),
            'ts': {'$gte': one_week_ago}
        }).sort([('ts', pymongo.ASCENDING)]).limit(100)
        for stat_record in week_ago_cursor:
            if 'members_cnt' in stat_record:
                week_ago_members_cnt = stat_record['members_cnt']
                break
        current_cursor = r2t.stats.find({'channel': channel.lower()}).sort([('ts', pymongo.DESCENDING)]).limit(100)
        for stat_record in current_cursor:
            if 'members_cnt' in stat_record:
                current_members_cnt = stat_record['members_cnt']
                break
        grow = current_members_cnt - week_ago_members_cnt
        if grow >= 10:
            top_growers[channel] = grow
    return sorted(top_growers, key=top_growers.get, reverse=True)[:3]
