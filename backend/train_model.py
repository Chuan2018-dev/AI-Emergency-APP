from app.ai import SeverityModel

if __name__ == "__main__":
    model = SeverityModel()
    model.train_and_save()
    print("Model trained and saved to data/model.pkl")
