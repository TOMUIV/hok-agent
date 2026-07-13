HERO_DB = {
    106: {"name": "小乔", "title": "Xiao Qiao"},
    107: {"name": "赵云", "title": "Zhao Yun"},
    108: {"name": "墨子", "title": "Mo Zi"},
    111: {"name": "孙尚香", "title": "Sun Shangxiang"},
    112: {"name": "鲁班", "title": "Lu Ban"},
    117: {"name": "钟无艳", "title": "Zhong Wuyan"},
    119: {"name": "扁鹊", "title": "Bian Que"},
    120: {"name": "白起", "title": "Bai Qi"},
    121: {"name": "芈月", "title": "Mi Yue"},
    123: {"name": "吕布", "title": "Lu Bu"},
    128: {"name": "曹操", "title": "Cao Cao"},
    130: {"name": "宫本武藏", "title": "Gongben Wuzang"},
    131: {"name": "李白", "title": "Li Bai"},
    132: {"name": "马可波罗", "title": "Marco Polo"},
    133: {"name": "狄仁杰", "title": "Di Renjie"},
    135: {"name": "项羽", "title": "Xiang Yu"},
    140: {"name": "关羽", "title": "Guan Yu"},
    141: {"name": "貂蝉", "title": "Diao Chan"},
    146: {"name": "露娜", "title": "Luna"},
    150: {"name": "韩信", "title": "Han Xin"},
    152: {"name": "王昭君", "title": "Wang Zhaojun"},
    154: {"name": "花木兰", "title": "Hua Mulan"},
    155: {"name": "艾琳", "title": "Ai Lin"},
    157: {"name": "不知火舞", "title": "Buzhihuowu"},
    163: {"name": "橘右京", "title": "Jvyoujing"},
    167: {"name": "孙悟空", "title": "Sun Wukong"},
    169: {"name": "后羿", "title": "Hou Yi"},
    173: {"name": "李元芳", "title": "Li Yuanfang"},
    174: {"name": "虞姬", "title": "Yu Ji"},
    175: {"name": "钟馗", "title": "Zhong Kui"},
    176: {"name": "杨玉环", "title": "Yang Yuhuan"},
    182: {"name": "干将莫邪", "title": "Ganjiang Moye"},
    189: {"name": "鬼谷子", "title": "Gui Guzi"},
    190: {"name": "诸葛亮", "title": "Zhuge Liang"},
    192: {"name": "黄忠", "title": "Huang Zhong"},
    193: {"name": "凯", "title": "Kai"},
    194: {"name": "苏烈", "title": "Su Lie"},
    196: {"name": "百里守约", "title": "Baili Shouyue"},
    199: {"name": "公孙离", "title": "Gongsun Li"},
    502: {"name": "裴擒虎", "title": "Pei Qinhou"},
    510: {"name": "孙策", "title": "Sun Ce"},
    513: {"name": "上官婉儿", "title": "Shangguan Waner"},
    522: {"name": "瑶", "title": "Yao"},
}

def hero_name(hid):
    return HERO_DB.get(hid, {}).get("name", f"Hero_{hid}")

CAMPS = ["None", "PLAYERCAMP_1", "PLAYERCAMP_2", "PLAYERCAMP_3", "PLAYERCAMP_4",
         "PLAYERCAMP_5", "PLAYERCAMP_6", "PLAYERCAMP_7", "PLAYERCAMP_8",
         "PLAYERCAMP_9", "PLAYERCAMP_10"]

def camp_name(camp_val):
    if isinstance(camp_val, int) and 0 <= camp_val < len(CAMPS):
        return CAMPS[camp_val]
    return str(camp_val)
