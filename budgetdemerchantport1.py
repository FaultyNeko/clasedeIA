import matplotlib.pyplot as plt

# Data processing from the log
sale_times = ["14:40:03", "14:40:08", "14:40:16", "14:40:21", "14:40:26", "14:40:34", "14:40:39", "14:40:44",
              "14:40:52", "14:40:57", "14:41:02", "14:41:10", "14:41:16", "14:41:21", "14:41:29", "14:41:34",
              "14:41:42", "14:41:52", "14:41:57", "14:42:07", "14:42:17", "14:42:22", "14:42:33", "14:42:43",
              "14:42:48", "14:42:58", "14:43:14"]
prices = [20, 20, 14, 20, 20, 14, 20, 20, 14, 20, 20, 14, 20, 20, 14, 20, 14, 10, 20, 10, 10, 20, 10, 10, 20, 10, 20]

# Merchants' budgets over time
merchant_budgets = {
    "RichMerchant_1": [500, 480, 480, 480, 480, 480, 480, 480, 480, 480, 480, 480, 480, 480, 480, 480, 480, 480, 460,
                       460, 460, 460, 460, 460, 440, 440, 440],
    "BasicMerchant_1": [100, 100, 100, 80, 80, 80, 60, 60, 60, 40, 40, 40, 20, 20, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                        0],
    "BasicMerchant_2": [100, 100, 100, 100, 80, 80, 80, 80, 80, 80, 80, 80, 80, 60, 60, 60, 40, 40, 40, 30, 30, 30, 30,
                        30, 10, 10, 10],
    "BasicMerchant_3": [100, 80, 80, 80, 80, 80, 80, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60,
                        60, 60, 60],
    "PoorMerchant_1": [50, 50, 36, 36, 36, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22,
                       22, 22, 22],
    "PoorMerchant_2": [50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 36, 36, 36, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22,
                       22, 22, 22]
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


plot_merchant_budgets()
