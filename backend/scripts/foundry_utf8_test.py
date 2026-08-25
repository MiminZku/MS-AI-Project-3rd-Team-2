import os
import json
import requests


def read_env_value(env_path, key):
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith(key + '='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        return None


def main():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    env_path = os.path.join(repo_root, '.env')

    api_key = read_env_value(env_path, 'AZURE_OPENAI_API_KEY')
    endpoint = read_env_value(env_path, 'AZURE_OPENAI_ENDPOINT')
    api_version = read_env_value(env_path, 'AZURE_OPENAI_API_VERSION')
    deployment = read_env_value(env_path, 'AZURE_OPENAI_CHAT_DEPLOYMENT')

    if not all([api_key, endpoint, api_version, deployment]):
        print('MISSING_ENV')
        return

    url = endpoint.rstrip('/') + f'/openai/deployments/{deployment}/chat/completions?api-version={api_version}'
    headers = {'api-key': api_key, 'Content-Type': 'application/json'}

    tests = [
        ('GREETING', '안녕하세요, 한국어로 2문장 인사해 주세요.'),
        ('EDIT', '다음 문장을 간결하게 줄여줘: "이 제품은 사용자 친화적이고 사용하기 쉽습니다. 또한 다양한 기능을 제공합니다."'),
        ('SUM', '아래 문단을 한 문장으로 요약해줘: "이번 연구는 신제품의 사용성 테스트를 통해 사용자의 만족도가 유의미하게 향상되었음을 보여준다. 참여자들은 인터페이스의 직관성, 반응속도, 그리고 전반적인 경험에 대해 긍정적인 평가를 내렸다."')
    ]

    for tag, msg in tests:
        payload = {'messages': [{'role': 'user', 'content': msg}]}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            resp.raise_for_status()
            body = resp.json()
            text = body.get('choices', [{}])[0].get('message', {}).get('content')
            print('===%s===' % tag)
            if text is None:
                print('NO_CONTENT')
                print(json.dumps(body, ensure_ascii=False, indent=2))
            else:
                print(text)
        except Exception as e:
            print('ERR', tag, str(e))


if __name__ == '__main__':
    main()
