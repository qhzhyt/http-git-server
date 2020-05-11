# 	"(.*?)/git-upload-pack$":                       Service{"POST", serviceRpc, "upload-pack"},
# 	"(.*?)/git-receive-pack$":                      Service{"POST", serviceRpc, "receive-pack"},
# 	"(.*?)/info/refs$":                             Service{"GET", getInfoRefs, ""},
# 	"(.*?)/HEAD$":                                  Service{"GET", getTextFile, ""},
# 	"(.*?)/objects/info/alternates$":               Service{"GET", getTextFile, ""},
# 	"(.*?)/objects/info/http-alternates$":          Service{"GET", getTextFile, ""},
# 	"(.*?)/objects/info/packs$":                    Service{"GET", getInfoPacks, ""},
# 	"(.*?)/objects/info/[^/]*$":                    Service{"GET", getTextFile, ""},
# 	"(.*?)/objects/[0-9a-f]{2}/[0-9a-f]{38}$":      Service{"GET", getLooseObject, ""},
# 	"(.*?)/objects/pack/pack-[0-9a-f]{40}\\.pack$": Service{"GET", getPackFile, ""},
# 	"(.*?)/objects/pack/pack-[0-9a-f]{40}\\.idx$":  Service{"GET", getIdxFile, ""},
import os
from gevent import monkey
from gevent.pywsgi import WSGIServer

from git import git_command_with_input, git_command

monkey.patch_all()

from flask import request, make_response, current_app, abort, json, jsonify, Response, Flask

from flask_httpauth import HTTPBasicAuth

from config import PROJECTS_PATH, GIT_REPOS_PATH, GIT_PATH, SERVER_HOST, SERVER_PORT, USER_NAME, PASSWORD

auth = HTTPBasicAuth()


@auth.verify_password
def verify_pw(username, password):
    return username == USER_NAME and password == PASSWORD


app = Flask(__name__, template_folder='../templates/')


@app.before_request
def git_before():
    # print(request.path)
    pass


@app.route('/<string:repo_name>/git-upload-pack', methods=['POST'])
@app.route('/<string:repo_name>.git/git-upload-pack', methods=['POST'])
def git_upload_pack(repo_name):
    # print(request.headers.get('Git-Protocol'))
    repo_name = repo_name + '.git'
    args = ['upload-pack', "--stateless-rpc", '.']
    res = git_command_with_input(repo_name, '', request.data, *args)

    return Response(res)


@app.route('/<string:repo_name>/git-receive-pack', methods=['POST'])
@app.route('/<string:repo_name>.git/git-receive-pack', methods=['POST'])
@auth.login_required
def git_receive_pack(repo_name):
    # push 操作需要验证
    repo = repo_name + '.git'
    old_version = request.headers.get('Git-Protocol')
    args = ['receive-pack', "--stateless-rpc", '.']
    res = git_command_with_input(repo, '', request.data, *args)
    return Response(res)


@app.route('/<string:repo_name>/info/refs', methods=['GET'])
@app.route('/<string:repo_name>.git/info/refs', methods=['GET'])
def git_info_refs(repo_name):
    repo_name = repo_name + '.git'

    repo_path = os.path.join(GIT_REPOS_PATH, repo_name)
    old_version = request.headers.get('Git-Protocol')
    version = request.headers.get('git/2.17.1')
    service = request.args.get('service')

    if service and 'git-' in service:
        service_name = service[4:]
    else:
        service_name = 'upload-pack'

    if service_name == 'receive-pack' and not auth.username():
        # push 操作需要验证
        return auth.login_required(git_info_refs)(repo_name)

    args = [service_name, "--stateless-rpc", "--advertise-refs", "."]

    res = git_command(repo_name, version, *args)

    first_line = '# service=git-%s\n0000' % service_name
    first_line = ('%.4x' % len(first_line)) + first_line

    resp = make_response(first_line + res.decode())
    resp.headers['Content-Type'] = 'application/x-git-%s-advertisement' % service_name
    return resp


WSGIServer((SERVER_HOST, SERVER_PORT), app).serve_forever()
