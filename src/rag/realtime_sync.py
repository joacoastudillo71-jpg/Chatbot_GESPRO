
import pathway as pw
import os

class StockMonitor:
    def __init__(self, data_file: str = "data/stock.csv"):
        self.data_file = data_file

    def run(self):
        """
        Starts the Pathway dataflow to monitor stock changes.
        """
        # Define the schema
        class StockSchema(pw.Schema):
            product_id: str
            name: str
            stock: int
            updated_at: str

        # Create a table from the CSV source. 
        # mode="streaming" allows it to react to new lines or changes if implemented with a connector that supports updates.
        # For simple CSV monitoring, we might reload or treat it as a stream of updates.
        # Here we assume a log-based CSV where new rows are updates.
        table = pw.io.csv.read(
            self.data_file,
            schema=StockSchema,
            mode="streaming"
        )

        # Filter for Out of Stock items (Real-time alert)
        out_of_stock = table.filter(pw.this.stock == 0)
        
        # We can also maintain a current state view
        # Group by product_id and take the last record (latest update)
        current_stock = table.reduce(
            product_id=pw.this.product_id,
            name=pw.reducers.max(pw.this.name), # Just to keep the name
            stock=pw.reducers.max(pw.this.stock), # Assuming purely additive log? No, we want the LATEST.
            # Pathway's reduce doesn't automatically imply "latest by time" unless we order it.
            # A better way for "latest state" in Pathway is usually maintain a state based on ID.
            # But for this simple implementation, let's just alert on the stream.
        )
        
        # Alert mechanism: pivot logic
        # In a real app, this would push to a webhook or update a shared state (like Redis).
        # Here we just print.
        pw.io.csv.write(out_of_stock, "data/out_of_stock_alerts.csv")
        
        # In a real integration with the bot, the bot checks a "Stock Service" 
        # which this Pathway application keeps updated in real-time.
        # For the prototype, we assume the bot reads from "data/current_stock_view.csv" or similar
        # which Pathway maintains.

        pw.run()

if __name__ == "__main__":
    # Create dummy file if not exists
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists("data/stock.csv"):
        with open("data/stock.csv", "w") as f:
            f.write("product_id,name,stock,updated_at\n")
            f.write("P001,Pijama Seda,10,2023-10-27T10:00:00\n")

    monitor = StockMonitor()
    monitor.run()
