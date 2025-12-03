#include <Data/Stream/DataSourceStream.h>

class StreamAdapter : public IDataSourceStream {
public:
    explicit StreamAdapter(Stream& stream) : stream(stream), finished(false) {}

    virtual uint16_t readMemoryBlock(char* data, int bufSize) override {
        int bytesRead = stream.readBytes(data, bufSize);
        if (bytesRead < bufSize) {
            finished = true; // Mark as finished if fewer bytes are read
        }
        return bytesRead;
    }

    virtual bool isFinished() override {
        return finished;
    }

    virtual StreamType getStreamType() const override {
        return eSST_Wrapper; // Indicate this is a wrapper stream
    }

private:
    Stream& stream;
    bool finished;
};