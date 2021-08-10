import json

from brownie import Contract, network, project
from flask import Flask
from flask_caching import Cache
from flask_cors import CORS


# flask stuff
cache = Cache(config={"CACHE_TYPE": "SimpleCache"})
app = Flask(__name__)
CORS(app)
cache.init_app(app)

# brownie stuff
network.connect("bsc-main")
p = project.load(".")
with open("abi/LQTYToken.abi.json") as f:
    flty_abi = json.load(f)
with open("abi/LQTYStaking.abi.json") as f:
    flty_staking_abi = json.load(f)
with open("abi/Multicall.abi.json") as f:
    multicall_abi = json.load(f)

# prepare contract data
flty = Contract.from_abi("FLTY", "0x83b325dbA77d55644619a4Ff29D42EE4487BCf31", flty_abi)
flty_staking = Contract.from_abi(
    "FLTYStaking", "0xb5543dBdd635c36a9a05E3B4b1bde3A7A4835309", flty_staking_abi
)
multicall = Contract.from_abi(
    "Multicall", "0x1Ee38d535d541c55C9dae27B12edf090C608E6Fb", multicall_abi
)

exclude = [
    "0x752d81c85D4b39b1aB1Dc9D96314cd9C9Af0a7F6",  # Community issuance, mining source
    "0x7F0AD9b60029740b37b74eB51e696ae483fC4Fc5",  # FLTY/BNB unipool, mining source
    "0x785f96028d85d98111f8B3Db8a8A0515d1D68C30",  # Gnosis safe, airdrop for LQTY holders
    "0x747b8E59F4B8D775F3404333Cf9B76Fe7b127e9C",  # Timelock
    "0x7C6f226db5401cdCC03434cdC02B6D5dB739FBe6",  # Team vesting lock-up
    "0xFdb73CEFb8A333642d65f025bACF5223922B8346",  # FLUSD/BUSD unipool, mining source
    "0x48487FCD9BA40cEfA0c5B5cb87523Fd7429126AF",  # FLUSD/BUSD unipool for dodo, mining source
]
multicall_data = [[str(flty), flty.balanceOf.encode_input(addr)] for addr in exclude]
# insert a query on total burned from staking contract
multicall_data.append([str(flty_staking), flty_staking.totalBurned.encode_input()])


@app.route("/total-supply")
def total_supply():
    return str(int(1e8))


@app.route("/circulating-supply")
@cache.cached(timeout=60)
def circulating_supply():
    # pylint: disable=global-statement
    global multicall, flty
    resp = multicall.aggregate.call(multicall_data)[1]
    decoded = [flty.balanceOf.decode_output(data) for data in resp]
    total = sum(decoded) / int(1e18)
    return "%.2f" % (int(1e8) - total)


@app.route("/total-burned")
@cache.cached(timeout=60)
def total_burned():
    # pylint: disable=global-statement
    global multicall, flty
    resp = multicall.aggregate.call(multicall_data)[1]
    # last item is info on total burned
    return "%.2f" % (flty.balanceOf.decode_output(resp[-1]) / int(1e18))
