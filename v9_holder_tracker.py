from collections import defaultdict
from web3 import Web3
TRANSFER_TOPIC=Web3.keccak(text="Transfer(address,address,uint256)").hex()

class HolderTracker:
    def __init__(self,w3):self.w3=w3
    def balances_from_transfers(self,token,from_block,to_block):
        logs=self.w3.eth.get_logs({"address":Web3.to_checksum_address(token),
            "topics":[TRANSFER_TOPIC],"fromBlock":from_block,"toBlock":to_block})
        b=defaultdict(int)
        for log in logs:
            if len(log["topics"])<3:continue
            sender=Web3.to_checksum_address("0x"+log["topics"][1].hex()[-40:])
            receiver=Web3.to_checksum_address("0x"+log["topics"][2].hex()[-40:])
            amount=int.from_bytes(log["data"],"big")
            if int(sender,16):b[sender]-=amount
            if int(receiver,16):b[receiver]+=amount
        return {a:v for a,v in b.items() if v>0}
    @staticmethod
    def concentration(balances,total_supply):
        if not balances or not total_supply:return None,[]
        ranked=sorted(balances.items(),key=lambda x:x[1],reverse=True)
        return ranked[0][1]/total_supply*100,[(a,v/total_supply*100) for a,v in ranked[:10]]
