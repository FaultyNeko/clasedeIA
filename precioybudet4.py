import matplotlib.pyplot as plt

# Data processing from the log
sale_times = [
    "17:06:48", "17:06:51", "17:06:54", "17:06:58", "17:07:06", "17:07:11", "17:07:19", "17:07:28",
    "17:07:33", "17:07:41", "17:07:46", "17:07:54", "17:08:05"
]
prices = [30, 28, 26, 14, 30, 20, 14, 14, 20, 14, 30, 24, 14]

# Merchants' budgets over time
merchant_budgets = {
    "RichMerchant_1": [500, 500, 500, 500, 500, 480, 480, 460, 460, 460, 440, 410, 396],
    "BasicMerchant_1": [100, 100, 100, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70],
    "BasicMerchant_2": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 70, 70, 70],
    "BasicMerchant_3": [100, 100, 100, 100, 86, 86, 86, 86, 56, 56, 56, 32, 32],
    "PoorMerchant_1": [50, 50, 50, 50, 50, 50, 36, 36, 36, 22, 22, 22, 8],
    "PoorMerchant_2": [50, 50, 50, 36, 36, 36, 22, 8, 8, 8, 8, 8, 8]
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
