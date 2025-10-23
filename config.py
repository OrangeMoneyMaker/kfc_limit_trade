class Config:
    def __init__(self):
        self.available_contracts = [
            {"chain_name":"arbitrum", "address_contract":'0x895D855a02946E736E493ff44b46a236f77C0C72'},
            {"chain_name":"ethereum", "address_contract":'0x895D855a02946E736E493ff44b46a236f77C0C72'},
            {"chain_name":"bsc", "address_contract":'0x895D855a02946E736E493ff44b46a236f77C0C72'},
            {"chain_name":"base", "address_contract":'0x895D855a02946E736E493ff44b46a236f77C0C72'}]
        
    async def get_available_contracts(self):
        return self.available_contracts