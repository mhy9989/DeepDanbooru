from io import BytesIO
import base64
import random
from PIL import Image
from hoshino import aiorequests,Service,priv
import re

sv_help = '''
- [鉴赏图片|鉴赏|aijp + 图片] 鉴赏图片获得对应tags
- [回复别人图片 + “鉴赏图片|鉴赏|aijp”] 对别人发图片进行鉴赏
'''.strip()

sv = Service(
    name = '鉴赏图片',  #功能名
    use_priv = priv.NORMAL, #使用权限   
    manage_priv = priv.ADMIN, #管理权限
    visible = True, #False隐藏
    enable_on_default = True, #是否默认启用
    bundle = '娱乐', #属于哪一类
    help_ = sv_help #帮助文本
    )

if_shape = True

class Error(Exception):
    def __init__(self, args: object) -> None:
        self.error = args

def randomhash(len=10):
    z = '0123456789abcdefghijklmnopqrstuvwxyz'
    hash = ''
    for _ in range(len):
        hash += random.choice(z)
    return hash

def pic2b64(pic: Image) -> str:
    buf = BytesIO()
    pic.save(buf, format='PNG')
    base64_str = base64.b64encode(buf.getvalue()).decode()
    return base64_str

async def get_image(bot, ev):
    reply = re.search(r"\[CQ:reply,id=(-?\d*)\](.*)", str(ev.message))
    if reply:
        tmid = reply.group(1)
        try:
            tmsg = await bot.get_msg(self_id=ev.self_id, message_id=int(tmid))
        except :
            await bot.finish(ev, '该消息已过期，请重新转发~')
        text = str(tmsg["message"])
    else:
        text = str(ev.message)
    img = re.search(r"\[CQ:image,file=(.*),url=(.*)\]", text)
    if not img:
        return None
    file = img.group(1)
    url = img.group(2)
    if 'c2cpicdw.qpic.cn/offpic_new/' in url:
        md5 = file[:-6].upper()
        url = f"http://gchat.qpic.cn/gchatpic_new/0/0-0-{md5}/0?term=2"
    resp = BytesIO(await (await aiorequests.get(url, stream=True)).content)
    image = Image.open(resp)
    return image

async def get_shape(image: Image) -> str:
    width, height = image.size
    if (width > height):
        shape = "Landscape"
    elif (width == height):
        shape = "Square"
    else:
        shape = "Portrait"
    return "&shape=" + shape


async def get_tags(image):
    url_push = 'https://hf.space/embed/hysts/DeepDanbooru/api/queue/push/'
    params = {
        "fn_index": 0,
        "data": [],
        "session_hash": randomhash(11),
        "action": "predict"
    }
    params['data'] = ['data:image/png;base64,' + pic2b64(image), 0.5]
    hash = (await (await aiorequests.post(url_push, json=params)).json())['hash']
    url_status = 'https://hf.space/embed/hysts/DeepDanbooru/api/queue/status/'
    while True:
        data = await (await aiorequests.post(url_status, json={'hash': hash})).json()
        if data['status'] == 'PENDING':
            continue
        elif data['status'] == 'COMPLETE':
            return data['data']['data'][0]['confidences']
        else:
            raise Error('tags请求错误')

@sv.on_keyword(('鉴赏图片','鉴赏','aijp'))
async def generate_tags(bot, ev):
    image = await get_image(bot, ev)
    shape = await get_shape(image)
    if not image:
        await bot.finish(ev, '未检测到可用图片', at_sender=True)
    await bot.send(ev,"少女鉴赏中...")
    json_tags = await get_tags(image)
    taglist = []
    if json_tags:
        for i in json_tags:
            if i["label"] != "rating:safe":
                taglist.append(i["label"])
        msg =  f"鉴赏的tags：\n" + ','.join(taglist)
        if if_shape:
            msg += shape
        await bot.send(ev, msg, at_sender=True)
    else:
        await bot.send(ev, '生成失败', at_sender=True)
