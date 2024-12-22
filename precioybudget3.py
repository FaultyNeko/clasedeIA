import matplotlib.pyplot as plt

# Data processing from the log
sale_times = [
    "16:46:41", "16:46:44", "16:46:48", "16:46:51", "16:46:55", "16:46:57", "16:47:05", "16:47:13",
    "16:47:21", "16:47:29", "16:47:39", "16:47:47", "16:48:03", "16:48:15", "16:48:25"
]
prices = [30, 28, 26, 24, 22, 20, 18, 16, 14, 12, 10, 14, 30, 14, 10]

# Merchants' budgets over time
merchant_budgets = {
    "RichMerchant_1": [500, 500, 500, 500, 500, 500, 500, 500, 500, 500, 500, 500, 470, 470, 470],
    "BasicMerchant_1": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 86, 86],
    "BasicMerchant_2": [100, 100, 100, 100, 100, 100, 100, 100, 100, 90, 80, 80, 80, 80, 70],
    "BasicMerchant_3": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 90, 90, 90, 80],
    "PoorMerchant_1": [50, 50, 50, 50, 50, 50, 50, 36, 36, 36, 22, 22, 22, 8, 8],
    "PoorMerchant_2": [50, 50, 50, 36, 36, 36, 36, 36, 22, 22, 22, 22, 22, 22, 22]
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
