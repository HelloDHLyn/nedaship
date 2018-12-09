provider "aws" {
    access_key = ""
    secret_key = ""
    region = "ap-northeast-2"
}

resource "aws_dynamodb_table" "NDSMedia" {
    name = "NDSMedia"
    read_capacity = 1
    write_capacity = 1
    hash_key = "MediaID"

    global_secondary_index {
        name = "UserIDIndex"
        hash_key = "UserID"
        read_capacity = 1
        write_capacity = 1
        projection_type = "KEYS_ONLY"
    }

    attribute {
        name = "MediaID"
        type = "N"
    }

    attribute {
        name = "UserID"
        type = "N"
    }
}

resource "aws_dynamodb_table" "NDSCursor" {
    name = "NDSCursor"
    read_capacity = 1
    write_capacity = 1
    hash_key = "UserID"

    attribute {
        name = "UserID"
        type = "N"
    }
}
