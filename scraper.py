import requests
import scraperwiki
from slackclient import SlackClient
from textwrap3 import wrap
from PIL import Image, ImageDraw, ImageFont
import io
from os import environ

def get_committee(data):
    committee = data['CommitteeChi']
    if committee == '':
        committee = data['SubcommitteeChi']
    return committee

def create_image(data):
    black = (255, 255, 255, 255)
    font_size = 50
    font_size_2 = 30
    fnt = ImageFont.truetype('Arial-Unicode-Regular.ttf', font_size)
    fnt2 = ImageFont.truetype('Arial-Unicode-Regular.ttf', font_size_2)
    img = Image.open('background2.png').convert('RGBA')
    draw = ImageDraw.Draw(img)
    lines = wrap(data['MeetingSubjectChi'], width=(int)(1200/font_size_2)) #1200/font_size
    committee = get_committee(data)
    draw.text((20, 20), committee + '就', font=fnt, fill=black)
    i = 0
    y = 0
    for line in lines:
        y = 30 + font_size + 20 + i * font_size_2
        draw.text((20, y), line, font=fnt2, fill=black)
        i += 1
        draw.text((20, 30 + y + font_size_2), u'邀請各界提交意見書', font=fnt, fill=black)
        deadline = data['SubmissionClosingDate'].split('T')[0]
        #截止日期
        draw.text((20, 500), u'截止日期：' + deadline, font=fnt, fill=black)
    bytes_io = io.BytesIO()
    img.save(bytes_io, format='PNG')
    bytes_io.seek(0)
    return bytes_io


headers = {'Cookie': 'AspxAutoDetectCookieSupport=1;PrinterFirendly=PrinterFirendly',
           'Accept-Encoding': 'gzip, deflate, br',
           'Content-Type': 'application/json;charset=utf-8',
           'X-Requested-With': 'XMLHttpRequest',
           'Referer': 'https://app3.legco.gov.hk/ors/chinese/List.aspx'}
req = requests.get('https://app3.legco.gov.hk/ors/api/Registrations/GetInvitations', headers=headers)
invitation_ids = [j['InvitationId'] for j in  req.json()]



TOKEN = environ['MORPH_TOKEN']
CHANNEL = environ['MORPH_CHANNEL']

for key in invitation_ids:
    r = requests.get('https://app3.legco.gov.hk/ors/api/Registrations/GetInvitation?invId=%d' % key)
    j = r.json()
    meeting = j['InvitationMeetings'][0]
    del j['InvitationMeetings']
    j.update(meeting)
    j['InvitationId'] = key
    existed = False
    try:
        existed = len(scraperwiki.sqlite.select('* from data where InvitationId = %d' % key)) > 0
    except:
        pass
    if not existed:
        img = create_image(j)
        slack = SlackClient(TOKEN)
        deadline = j['SubmissionClosingDate'].split('T')[0]
        committee = get_committee(j)
        s = committee + '就\'' + j['MeetingSubjectChi'] + '\'邀請各界提交意見書' + '\n'
        s += '會議議程及相關文件：\n' + j['RelevantPapersURLChi'] + '\n'
        s += '連結：\n' + 'http://app3.legco.gov.hk/ors/chinese/Invite.aspx?InvId=%d' % (key) + '\n'
        s += '截止日期：' + deadline + '\n'
        s += '#立法會 #意見書'
        print(slack.api_call('files.upload',
                       filename='%d.png' % (key),
                       channels=CHANNEL,
                       title='邀請各界提交意見書',
                       initial_comment=s,
                       file=img))
        scraperwiki.sqlite.save(unique_keys=['InvitationId'], data=j)
    else:
        print('%d already saved.' % key)
