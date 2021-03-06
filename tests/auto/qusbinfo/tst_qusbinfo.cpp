#include <QtTest/QtTest>
#include <QtUsb/QUsbInfo>

class tst_QUsbInfo : public QObject
{
    Q_OBJECT
public:
    explicit tst_QUsbInfo();

private slots:
    void constructors();
    void assignment();
    void features();

private:
};

tst_QUsbInfo::tst_QUsbInfo()
{
}

void tst_QUsbInfo::constructors()
{
    QUsbInfo info;

    QCOMPARE(info.logLevel(), QUsbDevice::logInfo);
}

void tst_QUsbInfo::assignment()
{
    QUsbInfo info;

    info.setLogLevel(QUsbDevice::logDebug);
    QCOMPARE(info.logLevel(), QUsbDevice::logDebug);

    info.setLogLevel(QUsbDevice::logNone);
    QCOMPARE(info.logLevel(), QUsbDevice::logNone);
}

void tst_QUsbInfo::features()
{
    QUsbInfo info;
    info.getPresentDevices();
}

QTEST_MAIN(tst_QUsbInfo)
#include "tst_qusbinfo.moc"
