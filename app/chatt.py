from gemini import chat_gem

def extract_bash_commands(text):
    # 入力文字列を行で分割
    lines = text.strip().split('\n')
    
    # 最初と最後の行を除外（スライシング使用）
    commands = lines
    
    # 特定の文字列（例: 'pattern1', 'pattern2'）を含む行を除去
    patterns_to_exclude = ['```bash', '```']
    filtered_commands = [
        command for command in commands 
        if not any(pattern in command for pattern in patterns_to_exclude)
    ]
    
    return filtered_commands
def chatLogic(user_input):
    print(f"userinput2   :{user_input}")
    
    instruct = f"""指示：ユーザーのアクションの理想が入力として提供されます。
    入力：{user_input}
    出力：詳細なactionlistを出力する。"""
    
    actionlist1 = chat_gem(instruct)
    print("11111===========================")
    print(actionlist1)
    actionlist = f"""指示：アクションリストが入力として提供される。
    入力：{actionlist1}
    コンテキスト：OSはLinuxです。
    出力：コマンドのみを改行刻みで列挙する。"""
    

    
    commandlist = chat_gem(actionlist)
    print("222222===========================")
    print(commandlist)
    list1=extract_bash_commands(commandlist)
    return list1
