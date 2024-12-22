import matplotlib.pyplot as plt

# Data processing from the log
sale_times = ["14:40:03", "14:40:08", "14:40:16", "14:40:21", "14:40:26", "14:40:34", "14:40:39", "14:40:44",
              "14:40:52", "14:40:57", "14:41:02", "14:41:10", "14:41:16", "14:41:21", "14:41:29", "14:41:34",
              "14:41:42", "14:41:52", "14:41:57", "14:42:07", "14:42:17", "14:42:22", "14:42:33", "14:42:43",
              "14:42:48", "14:42:58", "14:43:14"]
prices = [20, 20, 14, 20, 20, 14, 20, 20, 14, 20, 20, 14, 20, 20, 14, 20, 14, 10, 20, 10, 10, 20, 10, 10, 20, 10, 20]

# Convert times into indices for plotting
x = list(range(len(sale_times)))


# Plotting
def plot_fish_sales():
    plt.figure(figsize=(10, 6))
    plt.plot(x, prices, marker='o', linestyle='-', color='blue', label='Fish Prices')

    # Labels and title
    plt.xlabel('Auction Number (Sequential)', fontsize=12)
    plt.ylabel('Price (Units)', fontsize=12)
    plt.title('Auction Prices Over Time', fontsize=14)

    # x-axis with formatted times
    plt.xticks(ticks=x, labels=sale_times, rotation=45, fontsize=8)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()

    # Save and show
    plt.savefig('fish_sales_graph.png')
    plt.show()


plot_fish_sales()
