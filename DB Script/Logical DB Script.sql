CREATE TABLE Boxes (
    UniqueID NVARCHAR(255) PRIMARY KEY,
    TimeAtLocation1 DATETIME,
    Barcode NVARCHAR(255)
);

CREATE TABLE Items (
    UniqueID NVARCHAR(255) PRIMARY KEY,
    BoxID NVARCHAR(255),
    TimeAtLocation2 DATETIME,
    Barcode NVARCHAR(255),
    CONSTRAINT FK_Items_Boxes FOREIGN KEY (BoxID)
        REFERENCES Boxes(UniqueID)
);
