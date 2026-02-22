import time

class MockShop:
    def __init__(self):
        self.restock_called = 0
        self.last_restock_time = time.time()
        self.name = "Test Shop"
    def restock(self):
        self.restock_called += 1

def test_shop_logic():
    shop = MockShop()
    interval = 300 # 5 mins
    
    # Not time yet
    current_time = time.time()
    if current_time - shop.last_restock_time >= interval:
        shop.restock()
        shop.last_restock_time = current_time
    print(f"Restock called (0): {shop.restock_called}")
    
    # Fast forward (mock)
    shop.last_restock_time = current_time - 301
    if current_time - shop.last_restock_time >= interval:
        shop.restock()
        shop.last_restock_time = current_time
    print(f"Restock called (1): {shop.restock_called}")
    
    if shop.restock_called == 1:
        print("SHOP TIMER TEST PASCED")
    else:
        print("SHOP TIMER TEST FAILED")

if __name__ == "__main__":
    test_shop_logic()
