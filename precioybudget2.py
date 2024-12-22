import matplotlib.pyplot as plt

# Data processing from the log
sale_times = ["15:19:49", "15:19:54", "15:19:59", "15:20:07", "15:20:12", "15:20:17", "15:20:25", "15:20:30",
              "15:20:35", "15:20:43", "15:20:48", "15:20:54", "15:21:02", "15:21:07", "15:21:12"]
prices = [14, 20, 20, 14, 20, 20, 14, 20, 20, 14, 20, 20, 14, 20, 20]

# Merchants' budgets over time
merchant_budgets = {
    "RichMerchant_1": [500, 500, 480, 480, 480, 480, 480, 460, 460, 460, 440, 440, 440, 420, 420],
    "BasicMerchant_1": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
    "BasicMerchant_2": [100, 100, 100, 100, 80, 80, 80, 80, 60, 60, 60, 40, 40, 40, 20],
    "BasicMerchant_3": [100, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80],
    "PoorMerchant_1": [50, 50, 50, 36, 36, 36, 22, 22, 22, 22, 22, 22, 22, 22, 8],
    "PoorMerchant_2": [50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 36, 36, 36, 22, 22]
}

# Convert times into indices for plotting
x = list(range(len(sale_times)))


# Plotting
def plot_merchant_budgets():
    plt.figure(figsize=(12, 8))
    for merchant, budgets in merchant_budgets.items():
        plt.plot(x, budgets, marker='o', linestyle='-', label=merchant)

    # Labels and title
    plt.xlabel('Auction Number (Sequential)', fontsize=12)
    plt.ylabel('Remaining Budget (Units)', fontsize=12)
    plt.title('Merchants Budgets Over Time', fontsize=14)

    # x-axis with formatted times
    plt.xticks(ticks=x, labels=sale_times, rotation=45, fontsize=8)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()

    # Save and show
    plt.savefig('merchant_budgets_graph.png')
    plt.show()


def plot_prices_over_time():
    plt.figure(figsize=(12, 6))
    plt.plot(x, prices, marker='x', linestyle='-', color='red', label='Fish Prices')

    # Labels and title
    plt.xlabel('Auction Number (Sequential)', fontsize=12)
    plt.ylabel('Fish Price (Units)', fontsize=12)
    plt.title('Fish Prices Over Time', fontsize=14)

    # x-axis with formatted times
    plt.xticks(ticks=x, labels=sale_times, rotation=45, fontsize=8)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()

    # Save and show
    plt.savefig('fish_prices_graph.png')
    plt.show()


plot_merchant_budgets()
plot_prices_over_time()
